#!/usr/bin/env python3
"""
System Verification Script for Smart Grid Load Balancer
Tests all components to ensure the system is working correctly
"""

import requests
import time
import json
import sys
from datetime import datetime

class SystemVerifier:
    def __init__(self):
        self.base_urls = {
            'charge_request': 'http://localhost:5005',
            'load_balancer': 'http://localhost:5004',
            'substation_1': 'http://localhost:5001',
            'substation_2': 'http://localhost:5002',
            'substation_3': 'http://localhost:5003',
            'prometheus': 'http://localhost:9090',
            'grafana': 'http://localhost:3000'
        }
        self.results = []
        
    def log_result(self, test_name, success, message, details=None):
        """Log test result"""
        result = {
            'test': test_name,
            'success': success,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'details': details
        }
        self.results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        
        if details:
            print(f"   Details: {details}")
    
    def test_service_health(self, service_name, url):
        """Test if a service is healthy"""
        try:
            response = requests.get(f"{url}/health", timeout=5)
            if response.status_code == 200:
                data = response.json()
                self.log_result(f"{service_name} Health Check", True, "Service is healthy", data)
                return True
            else:
                self.log_result(f"{service_name} Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result(f"{service_name} Health Check", False, f"Connection failed: {str(e)}")
            return False
    
    def test_metrics_endpoint(self, service_name, url):
        """Test if metrics endpoint is accessible"""
        try:
            response = requests.get(f"{url}/metrics", timeout=5)
            if response.status_code == 200:
                self.log_result(f"{service_name} Metrics", True, "Metrics endpoint accessible")
                return True
            else:
                self.log_result(f"{service_name} Metrics", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result(f"{service_name} Metrics", False, f"Connection failed: {str(e)}")
            return False
    
    def test_substation_registration(self):
        """Test substation registration with load balancer"""
        try:
            # Get current substations
            response = requests.get(f"{self.base_urls['load_balancer']}/substations", timeout=5)
            if response.status_code == 200:
                data = response.json()
                substation_count = len(data.get('substations', []))
                self.log_result("Substation Registration", True, f"{substation_count} substations registered")
                return substation_count >= 3
            else:
                self.log_result("Substation Registration", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_result("Substation Registration", False, f"Connection failed: {str(e)}")
            return False
    
    def test_charging_request(self):
        """Test a complete charging request flow"""
        try:
            # Submit charging request
            request_data = {
                'ev_id': 'TEST_EV_001',
                'requested_kw': 22,
                'duration_minutes': 60
            }
            
            response = requests.post(
                f"{self.base_urls['charge_request']}/charge",
                json=request_data,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                session_id = result.get('session_id')
                substation_id = result.get('substation_id')
                
                self.log_result("Charging Request", True, 
                               f"Request successful - Session: {session_id}, Substation: {substation_id}")
                
                # Test stopping the session
                time.sleep(2)  # Let it charge for a bit
                
                stop_response = requests.delete(
                    f"{self.base_urls['charge_request']}/sessions/{session_id}",
                    timeout=5
                )
                
                if stop_response.status_code == 200:
                    self.log_result("Session Stop", True, "Session stopped successfully")
                    return True
                else:
                    self.log_result("Session Stop", False, f"HTTP {stop_response.status_code}")
                    return False
            else:
                self.log_result("Charging Request", False, f"HTTP {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Charging Request", False, f"Request failed: {str(e)}")
            return False
    
    def test_load_balancing(self):
        """Test load balancing by sending multiple requests"""
        try:
            requests_sent = 0
            successful_requests = 0
            substation_distribution = {}
            
            # Send 10 test requests
            for i in range(10):
                request_data = {
                    'ev_id': f'TEST_EV_{i:03d}',
                    'requested_kw': 11,
                    'duration_minutes': 30
                }
                
                response = requests.post(
                    f"{self.base_urls['charge_request']}/charge",
                    json=request_data,
                    timeout=5
                )
                
                requests_sent += 1
                
                if response.status_code == 200:
                    successful_requests += 1
                    result = response.json()
                    substation_id = result.get('substation_id')
                    substation_distribution[substation_id] = substation_distribution.get(substation_id, 0) + 1
                
                time.sleep(0.5)  # Small delay between requests
            
            success_rate = (successful_requests / requests_sent) * 100
            
            self.log_result("Load Balancing", True, 
                           f"Success rate: {success_rate:.1f}% ({successful_requests}/{requests_sent})",
                           f"Distribution: {substation_distribution}")
            
            return success_rate >= 80  # At least 80% success rate
            
        except Exception as e:
            self.log_result("Load Balancing", False, f"Test failed: {str(e)}")
            return False
    
    def test_monitoring_stack(self):
        """Test monitoring stack accessibility"""
        try:
            # Test Prometheus
            response = requests.get(f"{self.base_urls['prometheus']}/-/healthy", timeout=5)
            if response.status_code == 200:
                self.log_result("Prometheus Health", True, "Prometheus is healthy")
            else:
                self.log_result("Prometheus Health", False, f"HTTP {response.status_code}")
            
            # Test Grafana
            response = requests.get(f"{self.base_urls['grafana']}/api/health", timeout=5)
            if response.status_code == 200:
                self.log_result("Grafana Health", True, "Grafana is healthy")
            else:
                self.log_result("Grafana Health", False, f"HTTP {response.status_code}")
                
        except Exception as e:
            self.log_result("Monitoring Stack", False, f"Connection failed: {str(e)}")
    
    def run_all_tests(self):
        """Run all system tests"""
        print("🔍 Smart Grid Load Balancer - System Verification")
        print("=" * 60)
        
        # Test service health
        print("\n📊 Testing Service Health...")
        for service_name, url in self.base_urls.items():
            if service_name not in ['prometheus', 'grafana']:
                self.test_service_health(service_name, url)
        
        # Test metrics endpoints
        print("\n📈 Testing Metrics Endpoints...")
        for service_name, url in self.base_urls.items():
            if service_name not in ['prometheus', 'grafana']:
                self.test_metrics_endpoint(service_name, url)
        
        # Test substation registration
        print("\n🔗 Testing Substation Registration...")
        self.test_substation_registration()
        
        # Test charging request flow
        print("\n⚡ Testing Charging Request Flow...")
        self.test_charging_request()
        
        # Test load balancing
        print("\n⚖️ Testing Load Balancing...")
        self.test_load_balancing()
        
        # Test monitoring stack
        print("\n📊 Testing Monitoring Stack...")
        self.test_monitoring_stack()
        
        # Summary
        print("\n" + "=" * 60)
        print("📋 TEST SUMMARY")
        print("=" * 60)
        
        passed = sum(1 for result in self.results if result['success'])
        total = len(self.results)
        
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {total - passed}")
        print(f"Success Rate: {(passed/total)*100:.1f}%")
        
        if passed == total:
            print("\n🎉 All tests passed! System is working correctly.")
            return True
        else:
            print("\n⚠️ Some tests failed. Please check the system configuration.")
            return False
    
    def save_results(self, filename=None):
        """Save test results to file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"system_verification_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
        
        print(f"\n📄 Results saved to {filename}")

def main():
    verifier = SystemVerifier()
    
    try:
        success = verifier.run_all_tests()
        verifier.save_results()
        
        if success:
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 