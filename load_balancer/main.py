#!/usr/bin/env python3
"""
Dynamic Load Balancer for Smart Grid
Routes charging requests to the least loaded substation based on real-time metrics
"""

import time
import requests
import threading
from flask import Flask, jsonify, request
from prometheus_client import generate_latest, Counter, Gauge, Histogram, CONTENT_TYPE_LATEST
import logging
import json

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
requests_total = Counter('load_balancer_requests_total', 'Total requests processed')
routing_decisions = Counter('routing_decisions_total', 'Routing decisions made', ['substation_id'])
substation_load = Gauge('substation_load_percentage', 'Current load percentage', ['substation_id'])
polling_duration = Histogram('polling_duration_seconds', 'Time to poll substation metrics')

class LoadBalancer:
    def __init__(self):
        self.substations = []
        self.substation_metrics = {}
        self.lock = threading.Lock()
        self.polling_interval = 5  # seconds
        self.polling_thread = None
        self.running = False
        
    def add_substation(self, substation_url):
        """Add a substation to the load balancer"""
        with self.lock:
            if substation_url not in self.substations:
                self.substations.append(substation_url)
                logger.info(f"Added substation: {substation_url}")
                return True
            return False
    
    def remove_substation(self, substation_url):
        """Remove a substation from the load balancer"""
        with self.lock:
            if substation_url in self.substations:
                self.substations.remove(substation_url)
                if substation_url in self.substation_metrics:
                    del self.substation_metrics[substation_url]
                logger.info(f"Removed substation: {substation_url}")
                return True
            return False
    
    def poll_substation_metrics(self, substation_url):
        """Poll metrics from a single substation"""
        try:
            start_time = time.time()
            response = requests.get(f"{substation_url}/metrics", timeout=5)
            polling_duration.observe(time.time() - start_time)
            
            if response.status_code == 200:
                # Parse Prometheus metrics to extract current_load and total_capacity
                metrics_text = response.text
                current_load = 0
                total_capacity = 1
                
                for line in metrics_text.split('\n'):
                    if line.startswith('current_load '):
                        current_load = float(line.split(' ')[1])
                    elif line.startswith('total_capacity '):
                        total_capacity = float(line.split(' ')[1])
                
                load_percentage = (current_load / total_capacity) * 100 if total_capacity > 0 else 0
                
                with self.lock:
                    self.substation_metrics[substation_url] = {
                        'current_load': current_load,
                        'total_capacity': total_capacity,
                        'load_percentage': load_percentage,
                        'last_updated': time.time()
                    }
                    
                    # Update Prometheus metrics
                    substation_id = substation_url.split('/')[-1] if substation_url.endswith('/') else substation_url.split('/')[-1]
                    substation_load.labels(substation_id=substation_id).set(load_percentage)
                
                logger.debug(f"Updated metrics for {substation_url}: {load_percentage:.2f}% load")
                return True
            else:
                logger.warning(f"Failed to poll {substation_url}: HTTP {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error polling {substation_url}: {e}")
            return False
    
    def poll_all_substations(self):
        """Poll metrics from all substations"""
        while self.running:
            with self.lock:
                substations_to_poll = self.substations.copy()
            
            for substation_url in substations_to_poll:
                self.poll_substation_metrics(substation_url)
            
            time.sleep(self.polling_interval)
    
    def get_least_loaded_substation(self):
        """Get the substation with the lowest load percentage"""
        with self.lock:
            if not self.substation_metrics:
                return None
            
            least_loaded = min(self.substation_metrics.items(), 
                             key=lambda x: x[1]['load_percentage'])
            return least_loaded[0]
    
    def route_charging_request(self, ev_id, requested_kw):
        """Route a charging request to the least loaded substation"""
        substation_url = self.get_least_loaded_substation()
        
        if not substation_url:
            return None, "No available substations"
        
        try:
            response = requests.post(
                f"{substation_url}/charge",
                json={'ev_id': ev_id, 'requested_kw': requested_kw},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                substation_id = substation_url.split('/')[-1] if substation_url.endswith('/') else substation_url.split('/')[-1]
                routing_decisions.labels(substation_id=substation_id).inc()
                return result, None
            else:
                return None, f"Substation error: {response.status_code}"
                
        except Exception as e:
            logger.error(f"Error routing to {substation_url}: {e}")
            return None, str(e)
    
    def start_polling(self):
        """Start the polling thread"""
        if not self.running:
            self.running = True
            self.polling_thread = threading.Thread(target=self.poll_all_substations, daemon=True)
            self.polling_thread.start()
            logger.info("Started substation polling")
    
    def stop_polling(self):
        """Stop the polling thread"""
        self.running = False
        if self.polling_thread:
            self.polling_thread.join()
            logger.info("Stopped substation polling")
    
    def get_status(self):
        """Get load balancer status"""
        with self.lock:
            return {
                'substations': len(self.substations),
                'active_substations': len(self.substation_metrics),
                'substation_metrics': self.substation_metrics.copy(),
                'polling_interval': self.polling_interval,
                'running': self.running
            }

# Initialize load balancer
load_balancer = LoadBalancer()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'load_balancer',
        'timestamp': time.time()
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Get load balancer status"""
    return jsonify(load_balancer.get_status())

@app.route('/substations', methods=['GET'])
def list_substations():
    """List all registered substations"""
    with load_balancer.lock:
        return jsonify({
            'substations': load_balancer.substations,
            'metrics': load_balancer.substation_metrics
        })

@app.route('/substations', methods=['POST'])
def add_substation():
    """Add a substation to the load balancer"""
    try:
        data = request.get_json()
        substation_url = data.get('substation_url')
        
        if not substation_url:
            return jsonify({'error': 'substation_url is required'}), 400
        
        success = load_balancer.add_substation(substation_url)
        
        if success:
            return jsonify({'status': 'added', 'substation_url': substation_url})
        else:
            return jsonify({'error': 'Substation already exists'}), 409
            
    except Exception as e:
        logger.error(f"Error adding substation: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/substations/<path:substation_url>', methods=['DELETE'])
def remove_substation(substation_url):
    """Remove a substation from the load balancer"""
    try:
        success = load_balancer.remove_substation(substation_url)
        
        if success:
            return jsonify({'status': 'removed', 'substation_url': substation_url})
        else:
            return jsonify({'error': 'Substation not found'}), 404
            
    except Exception as e:
        logger.error(f"Error removing substation: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/charge', methods=['POST'])
def route_charging_request():
    """Route a charging request to the least loaded substation"""
    try:
        data = request.get_json()
        ev_id = data.get('ev_id')
        requested_kw = data.get('requested_kw', 10)
        
        if not ev_id:
            return jsonify({'error': 'ev_id is required'}), 400
        
        requests_total.inc()
        
        result, error = load_balancer.route_charging_request(ev_id, requested_kw)
        
        if result:
            return jsonify(result)
        else:
            return jsonify({'error': error}), 503
            
    except Exception as e:
        logger.error(f"Error routing charging request: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with basic info"""
    return jsonify({
        'service': 'load_balancer',
        'endpoints': {
            'health': '/health',
            'status': '/status',
            'substations': '/substations (GET/POST)',
            'charge': '/charge (POST)',
            'metrics': '/metrics'
        }
    })

if __name__ == '__main__':
    logger.info("Starting Load Balancer Service")
    
    # Start polling thread
    load_balancer.start_polling()
    
    try:
        app.run(host='0.0.0.0', port=5001, debug=False)
    finally:
        load_balancer.stop_polling() 