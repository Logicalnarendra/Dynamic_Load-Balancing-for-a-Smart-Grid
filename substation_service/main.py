#!/usr/bin/env python3
"""
Substation Service for Smart Grid Load Balancer
Simulates a charging substation and exposes load metrics via Prometheus
"""

import time
import random
import threading
from flask import Flask, jsonify
from prometheus_client import generate_latest, Counter, Gauge, Histogram, CONTENT_TYPE_LATEST
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
charging_requests_total = Counter('charging_requests_total', 'Total number of charging requests')
charging_duration_seconds = Histogram('charging_duration_seconds', 'Time spent charging')
current_load = Gauge('current_load', 'Current load percentage of the substation')
active_chargers = Gauge('active_chargers', 'Number of active chargers')
total_capacity = Gauge('total_capacity', 'Total charging capacity in kW')

# Substation state
class SubstationState:
    def __init__(self, substation_id, max_capacity=100):
        self.substation_id = substation_id
        self.max_capacity = max_capacity
        self.current_load = 0
        self.active_chargers = 0
        self.charging_sessions = {}
        self.lock = threading.Lock()
        
        # Initialize metrics
        total_capacity.set(max_capacity)
        current_load.set(0)
        active_chargers.set(0)
    
    def start_charging(self, ev_id, requested_kw):
        with self.lock:
            if self.current_load + requested_kw <= self.max_capacity:
                session_id = f"{self.substation_id}_{ev_id}_{int(time.time())}"
                self.charging_sessions[session_id] = {
                    'ev_id': ev_id,
                    'requested_kw': requested_kw,
                    'start_time': time.time(),
                    'status': 'charging'
                }
                self.current_load += requested_kw
                self.active_chargers += 1
                
                # Update metrics
                current_load.set(self.current_load)
                active_chargers.set(self.active_chargers)
                charging_requests_total.inc()
                
                logger.info(f"Started charging session {session_id} for EV {ev_id} with {requested_kw}kW")
                return session_id
            else:
                logger.warning(f"Cannot start charging for EV {ev_id}: insufficient capacity")
                return None
    
    def stop_charging(self, session_id):
        with self.lock:
            if session_id in self.charging_sessions:
                session = self.charging_sessions[session_id]
                duration = time.time() - session['start_time']
                
                self.current_load -= session['requested_kw']
                self.active_chargers -= 1
                
                # Update metrics
                current_load.set(self.current_load)
                active_chargers.set(self.active_chargers)
                charging_duration_seconds.observe(duration)
                
                del self.charging_sessions[session_id]
                logger.info(f"Stopped charging session {session_id} after {duration:.2f} seconds")
                return True
            return False
    
    def get_status(self):
        with self.lock:
            return {
                'substation_id': self.substation_id,
                'current_load': self.current_load,
                'max_capacity': self.max_capacity,
                'load_percentage': (self.current_load / self.max_capacity) * 100,
                'active_chargers': self.active_chargers,
                'available_capacity': self.max_capacity - self.current_load
            }

# Initialize substation
substation = SubstationState(
    substation_id=random.randint(1000, 9999),
    max_capacity=random.randint(80, 120)
)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'substation_id': substation.substation_id,
        'timestamp': time.time()
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Get current substation status"""
    return jsonify(substation.get_status())

@app.route('/charge', methods=['POST'])
def start_charging():
    """Start a charging session"""
    try:
        data = request.get_json()
        ev_id = data.get('ev_id')
        requested_kw = data.get('requested_kw', 10)
        
        if not ev_id:
            return jsonify({'error': 'ev_id is required'}), 400
        
        session_id = substation.start_charging(ev_id, requested_kw)
        
        if session_id:
            return jsonify({
                'session_id': session_id,
                'status': 'started',
                'substation_id': substation.substation_id
            })
        else:
            return jsonify({'error': 'Insufficient capacity'}), 503
            
    except Exception as e:
        logger.error(f"Error starting charging: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/charge/<session_id>', methods=['DELETE'])
def stop_charging(session_id):
    """Stop a charging session"""
    try:
        success = substation.stop_charging(session_id)
        if success:
            return jsonify({'status': 'stopped', 'session_id': session_id})
        else:
            return jsonify({'error': 'Session not found'}), 404
    except Exception as e:
        logger.error(f"Error stopping charging: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with basic info"""
    return jsonify({
        'service': 'substation_service',
        'substation_id': substation.substation_id,
        'endpoints': {
            'health': '/health',
            'status': '/status',
            'metrics': '/metrics',
            'charge': '/charge (POST)',
            'stop_charge': '/charge/<session_id> (DELETE)'
        }
    })

if __name__ == '__main__':
    # Add missing import
    from flask import request
    
    logger.info(f"Starting Substation Service with ID: {substation.substation_id}")
    logger.info(f"Max capacity: {substation.max_capacity}kW")
    
    app.run(host='0.0.0.0', port=5000, debug=False) 