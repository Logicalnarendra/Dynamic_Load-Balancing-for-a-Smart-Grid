#!/usr/bin/env python3
"""
Charge Request Service for Smart Grid Load Balancer
Public entry point for EV charging requests
"""

import time
import requests
import threading
from flask import Flask, jsonify, request
from prometheus_client import generate_latest, Counter, Gauge, Histogram, CONTENT_TYPE_LATEST
import logging
import json
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Prometheus metrics
requests_total = Counter('charge_requests_total', 'Total charging requests received')
requests_duration = Histogram('charge_requests_duration_seconds', 'Time to process charging requests')
active_sessions = Gauge('active_sessions', 'Number of active charging sessions')
failed_requests = Counter('failed_requests_total', 'Total failed requests')

class ChargeRequestService:
    def __init__(self):
        self.load_balancer_url = os.getenv('LOAD_BALANCER_URL', 'http://load_balancer:5001')
        self.active_sessions = {}
        self.lock = threading.Lock()
        
    def submit_charging_request(self, ev_id, requested_kw, duration_minutes=None):
        """Submit a charging request to the load balancer"""
        try:
            start_time = time.time()
            
            response = requests.post(
                f"{self.load_balancer_url}/charge",
                json={
                    'ev_id': ev_id,
                    'requested_kw': requested_kw
                },
                timeout=30
            )
            
            requests_duration.observe(time.time() - start_time)
            
            if response.status_code == 200:
                result = response.json()
                session_id = result.get('session_id')
                
                if session_id:
                    with self.lock:
                        self.active_sessions[session_id] = {
                            'ev_id': ev_id,
                            'requested_kw': requested_kw,
                            'substation_id': result.get('substation_id'),
                            'start_time': time.time(),
                            'duration_minutes': duration_minutes
                        }
                        active_sessions.set(len(self.active_sessions))
                    
                    logger.info(f"Started charging session {session_id} for EV {ev_id}")
                    return result
                else:
                    failed_requests.inc()
                    return {'error': 'No session ID returned'}
            else:
                failed_requests.inc()
                return {'error': f'Load balancer error: {response.status_code}'}
                
        except Exception as e:
            failed_requests.inc()
            logger.error(f"Error submitting charging request: {e}")
            return {'error': str(e)}
    
    def stop_charging_session(self, session_id):
        """Stop a charging session"""
        try:
            with self.lock:
                if session_id not in self.active_sessions:
                    return {'error': 'Session not found'}
                
                session = self.active_sessions[session_id]
                substation_id = session['substation_id']
            
            # Find the substation URL and stop the session
            # This is a simplified approach - in a real system, you'd track substation URLs
            substation_url = f"http://substation_{substation_id}:5000"
            
            response = requests.delete(
                f"{substation_url}/charge/{session_id}",
                timeout=10
            )
            
            if response.status_code == 200:
                with self.lock:
                    del self.active_sessions[session_id]
                    active_sessions.set(len(self.active_sessions))
                
                logger.info(f"Stopped charging session {session_id}")
                return {'status': 'stopped', 'session_id': session_id}
            else:
                return {'error': f'Failed to stop session: {response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error stopping charging session: {e}")
            return {'error': str(e)}
    
    def get_active_sessions(self):
        """Get all active charging sessions"""
        with self.lock:
            return self.active_sessions.copy()
    
    def get_status(self):
        """Get service status"""
        return {
            'service': 'charge_request_service',
            'load_balancer_url': self.load_balancer_url,
            'active_sessions': len(self.active_sessions),
            'timestamp': time.time()
        }

# Initialize service
charge_service = ChargeRequestService()

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'charge_request_service',
        'timestamp': time.time()
    })

@app.route('/status', methods=['GET'])
def get_status():
    """Get service status"""
    return jsonify(charge_service.get_status())

@app.route('/charge', methods=['POST'])
def submit_charging_request():
    """Submit a charging request"""
    try:
        data = request.get_json()
        ev_id = data.get('ev_id')
        requested_kw = data.get('requested_kw', 10)
        duration_minutes = data.get('duration_minutes')
        
        if not ev_id:
            return jsonify({'error': 'ev_id is required'}), 400
        
        requests_total.inc()
        
        result = charge_service.submit_charging_request(ev_id, requested_kw, duration_minutes)
        
        if 'error' in result:
            return jsonify(result), 503
        else:
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error processing charging request: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/sessions', methods=['GET'])
def get_sessions():
    """Get all active charging sessions"""
    return jsonify(charge_service.get_active_sessions())

@app.route('/sessions/<session_id>', methods=['DELETE'])
def stop_session(session_id):
    """Stop a charging session"""
    try:
        result = charge_service.stop_charging_session(session_id)
        
        if 'error' in result:
            return jsonify(result), 404
        else:
            return jsonify(result)
            
    except Exception as e:
        logger.error(f"Error stopping session: {e}")
        return jsonify({'error': 'Internal server error'}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus metrics endpoint"""
    return generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST}

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with basic info"""
    return jsonify({
        'service': 'charge_request_service',
        'description': 'Public entry point for EV charging requests',
        'endpoints': {
            'health': '/health',
            'status': '/status',
            'charge': '/charge (POST)',
            'sessions': '/sessions (GET)',
            'stop_session': '/sessions/<session_id> (DELETE)',
            'metrics': '/metrics'
        }
    })

if __name__ == '__main__':
    logger.info("Starting Charge Request Service")
    logger.info(f"Load balancer URL: {charge_service.load_balancer_url}")
    
    app.run(host='0.0.0.0', port=5002, debug=False) 