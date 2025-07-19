#!/usr/bin/env python3
"""
Load Tester for Smart Grid Load Balancer
Simulates rush hour EV charging requests to test system performance
"""

import time
import requests
import threading
import random
import json
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import argparse
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LoadTester:
    def __init__(self, base_url="http://localhost:5002"):
        self.base_url = base_url
        self.results = []
        self.lock = threading.Lock()
        self.session_ids = []
        
    def generate_ev_request(self):
        """Generate a realistic EV charging request"""
        ev_id = f"EV_{random.randint(1000, 9999)}"
        requested_kw = random.choice([7, 11, 22, 50])  # Common EV charging rates
        duration_minutes = random.randint(30, 240)  # 30 minutes to 4 hours
        
        return {
            'ev_id': ev_id,
            'requested_kw': requested_kw,
            'duration_minutes': duration_minutes
        }
    
    def submit_charging_request(self, request_id):
        """Submit a single charging request"""
        try:
            request_data = self.generate_ev_request()
            start_time = time.time()
            
            response = requests.post(
                f"{self.base_url}/charge",
                json=request_data,
                timeout=30
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            result = {
                'request_id': request_id,
                'ev_id': request_data['ev_id'],
                'requested_kw': request_data['requested_kw'],
                'duration_minutes': request_data['duration_minutes'],
                'response_time': duration,
                'status_code': response.status_code,
                'success': response.status_code == 200,
                'timestamp': start_time
            }
            
            if response.status_code == 200:
                response_data = response.json()
                result['session_id'] = response_data.get('session_id')
                result['substation_id'] = response_data.get('substation_id')
                
                with self.lock:
                    self.session_ids.append(result['session_id'])
                
                logger.info(f"Request {request_id}: EV {request_data['ev_id']} assigned to substation {result['substation_id']}")
            else:
                logger.warning(f"Request {request_id}: Failed with status {response.status_code}")
            
            with self.lock:
                self.results.append(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Request {request_id}: Error - {e}")
            result = {
                'request_id': request_id,
                'ev_id': request_data['ev_id'] if 'request_data' in locals() else 'unknown',
                'requested_kw': request_data['requested_kw'] if 'request_data' in locals() else 0,
                'duration_minutes': request_data['duration_minutes'] if 'request_data' in locals() else 0,
                'response_time': time.time() - start_time if 'start_time' in locals() else 0,
                'status_code': 0,
                'success': False,
                'error': str(e),
                'timestamp': time.time()
            }
            
            with self.lock:
                self.results.append(result)
            
            return result
    
    def run_load_test(self, num_requests, concurrent_users, ramp_up_seconds=60):
        """Run the load test with specified parameters"""
        logger.info(f"Starting load test: {num_requests} requests, {concurrent_users} concurrent users")
        logger.info(f"Ramp-up time: {ramp_up_seconds} seconds")
        
        start_time = time.time()
        
        # Calculate delay between requests for ramp-up
        if ramp_up_seconds > 0:
            delay_between_requests = ramp_up_seconds / num_requests
        else:
            delay_between_requests = 0
        
        with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
            futures = []
            
            for i in range(num_requests):
                if delay_between_requests > 0:
                    time.sleep(delay_between_requests)
                
                future = executor.submit(self.submit_charging_request, i + 1)
                futures.append(future)
            
            # Wait for all requests to complete
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    logger.error(f"Future execution error: {e}")
        
        end_time = time.time()
        total_duration = end_time - start_time
        
        logger.info(f"Load test completed in {total_duration:.2f} seconds")
        return total_duration
    
    def get_system_status(self):
        """Get current system status"""
        try:
            # Get charge request service status
            response = requests.get(f"{self.base_url}/status", timeout=5)
            if response.status_code == 200:
                return response.json()
            else:
                return {'error': f'Status check failed: {response.status_code}'}
        except Exception as e:
            return {'error': f'Status check error: {e}'}
    
    def analyze_results(self):
        """Analyze the test results"""
        if not self.results:
            return "No results to analyze"
        
        successful_requests = [r for r in self.results if r['success']]
        failed_requests = [r for r in self.results if not r['success']]
        
        response_times = [r['response_time'] for r in successful_requests]
        
        analysis = {
            'total_requests': len(self.results),
            'successful_requests': len(successful_requests),
            'failed_requests': len(failed_requests),
            'success_rate': len(successful_requests) / len(self.results) * 100,
            'response_time_stats': {
                'mean': statistics.mean(response_times) if response_times else 0,
                'median': statistics.median(response_times) if response_times else 0,
                'min': min(response_times) if response_times else 0,
                'max': max(response_times) if response_times else 0,
                'std_dev': statistics.stdev(response_times) if len(response_times) > 1 else 0
            },
            'substation_distribution': {},
            'power_distribution': {}
        }
        
        # Analyze substation distribution
        substation_counts = {}
        power_usage = {}
        
        for result in successful_requests:
            substation_id = result.get('substation_id', 'unknown')
            substation_counts[substation_id] = substation_counts.get(substation_id, 0) + 1
            
            requested_kw = result.get('requested_kw', 0)
            power_usage[requested_kw] = power_usage.get(requested_kw, 0) + 1
        
        analysis['substation_distribution'] = substation_counts
        analysis['power_distribution'] = power_usage
        
        return analysis
    
    def print_results(self):
        """Print formatted test results"""
        analysis = self.analyze_results()
        
        print("\n" + "="*60)
        print("LOAD TEST RESULTS")
        print("="*60)
        
        if isinstance(analysis, str):
            print(analysis)
            return
        
        print(f"Total Requests: {analysis['total_requests']}")
        print(f"Successful Requests: {analysis['successful_requests']}")
        print(f"Failed Requests: {analysis['failed_requests']}")
        print(f"Success Rate: {analysis['success_rate']:.2f}%")
        
        print("\nResponse Time Statistics:")
        rt_stats = analysis['response_time_stats']
        print(f"  Mean: {rt_stats['mean']:.3f}s")
        print(f"  Median: {rt_stats['median']:.3f}s")
        print(f"  Min: {rt_stats['min']:.3f}s")
        print(f"  Max: {rt_stats['max']:.3f}s")
        print(f"  Std Dev: {rt_stats['std_dev']:.3f}s")
        
        print("\nSubstation Distribution:")
        for substation_id, count in analysis['substation_distribution'].items():
            percentage = (count / analysis['successful_requests']) * 100
            print(f"  Substation {substation_id}: {count} requests ({percentage:.1f}%)")
        
        print("\nPower Distribution:")
        for power, count in analysis['power_distribution'].items():
            percentage = (count / analysis['successful_requests']) * 100
            print(f"  {power}kW: {count} requests ({percentage:.1f}%)")
        
        print("="*60)
    
    def save_results(self, filename=None):
        """Save test results to a JSON file"""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"load_test_results_{timestamp}.json"
        
        data = {
            'test_info': {
                'timestamp': datetime.now().isoformat(),
                'base_url': self.base_url,
                'total_requests': len(self.results)
            },
            'results': self.results,
            'analysis': self.analyze_results()
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Results saved to {filename}")

def main():
    parser = argparse.ArgumentParser(description='Load Tester for Smart Grid Load Balancer')
    parser.add_argument('--url', default='http://localhost:5002', help='Base URL for the charge request service')
    parser.add_argument('--requests', type=int, default=100, help='Number of requests to send')
    parser.add_argument('--concurrent', type=int, default=10, help='Number of concurrent users')
    parser.add_argument('--ramp-up', type=int, default=60, help='Ramp-up time in seconds')
    parser.add_argument('--save', help='Save results to specified file')
    
    args = parser.parse_args()
    
    # Create load tester
    tester = LoadTester(args.url)
    
    # Check system status before starting
    logger.info("Checking system status...")
    status = tester.get_system_status()
    logger.info(f"System status: {status}")
    
    # Run the load test
    try:
        total_duration = tester.run_load_test(args.requests, args.concurrent, args.ramp_up)
        
        # Print results
        tester.print_results()
        
        # Save results if requested
        if args.save:
            tester.save_results(args.save)
        else:
            tester.save_results()  # Save with default filename
        
        logger.info(f"Load test completed successfully in {total_duration:.2f} seconds")
        
    except KeyboardInterrupt:
        logger.info("Load test interrupted by user")
    except Exception as e:
        logger.error(f"Load test failed: {e}")

if __name__ == '__main__':
    main() 