"""Load testing script for inventory.ai API."""
import requests
import time
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict
import json

# API Configuration
API_BASE_URL = "http://inventory-ai-alb-755465244.us-east-1.elb.amazonaws.com"

# Auth0 Configuration (from config.json)
AUTH0_DOMAIN = "dev-8jwmstalyswjk6k6.us.auth0.com"
AUTH0_CLIENT_ID= "pzavIBiATNt20mTgnqRSlAxQDh88uPgl"
AUTH0_CLIENT_SECRET= "uyZ-cRCI01CC0dgWXq_vsa8Mazc8HMBCUc62crRqLrjrro5ga4GsJTMAPAdtos_d"
AUTH0_AUDIENCE = "https://dev-8jwmstalyswjk6k6.us.auth0.com/api/v2/"


def get_auth_token():
    """Get Auth0 token for authenticated requests."""
    try:
        response = requests.post(
            f"https://{AUTH0_DOMAIN}/oauth/token",
            json={
                'client_id': AUTH0_CLIENT_ID,
                'client_secret': AUTH0_CLIENT_SECRET,
                'audience': AUTH0_AUDIENCE,
                'grant_type': 'client_credentials'
            },
            timeout=10
        )
        return response.json()['access_token']
    except Exception as e:
        print(f"Warning: Could not get auth token: {e}")
        return None


def make_request(endpoint: str, method: str = "GET", auth_required: bool = False, data: dict = None):
    """Make a single request and measure response time."""
    url = f"{API_BASE_URL}{endpoint}"
    headers = {}
    
    if auth_required:
        token = get_auth_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
    
    start_time = time.time()
    
    try:
        if method == "GET":
            response = requests.get(url, headers=headers, timeout=10)
        elif method == "POST":
            response = requests.post(url, json=data, headers=headers, timeout=10)
        
        elapsed_ms = (time.time() - start_time) * 1000
        
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": response.status_code,
            "response_time_ms": elapsed_ms,
            "success": 200 <= response.status_code < 300
        }
    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        return {
            "endpoint": endpoint,
            "method": method,
            "status_code": 0,
            "response_time_ms": elapsed_ms,
            "success": False,
            "error": str(e)
        }


def load_test(num_requests: int = 100, concurrent_users: int = 10):
    """
    Perform load test with multiple concurrent requests.
    
    Args:
        num_requests: Total number of requests to make
        concurrent_users: Number of concurrent threads
    """
    print("="*80)
    print("INVENTORY.AI API LOAD TEST")
    print("="*80)
    print(f"Target: {API_BASE_URL}")
    print(f"Total Requests: {num_requests}")
    print(f"Concurrent Users: {concurrent_users}")
    print("="*80)
    
    # Define test scenarios
    test_endpoints = [
        {"endpoint": "/health", "method": "GET", "weight": 30},
        {"endpoint": "/", "method": "GET", "weight": 10},
        {"endpoint": "/docs", "method": "GET", "weight": 5},
        {"endpoint": "/products?skip=0&limit=10", "method": "GET", "weight": 20},
        {"endpoint": "/products?skip=10&limit=10", "method": "GET", "weight": 10},
        {"endpoint": "/search/text", "method": "POST", "weight": 15, 
         "data": {"query": "wheelchair", "top_k": 5}},
        {"endpoint": "/search/text", "method": "POST", "weight": 10,
         "data": {"query": "hospital bed", "top_k": 5}},
    ]
    
    # Generate weighted request list
    requests_to_make = []
    total_weight = sum(t["weight"] for t in test_endpoints)
    
    for test in test_endpoints:
        count = int((test["weight"] / total_weight) * num_requests)
        for _ in range(count):
            requests_to_make.append({
                "endpoint": test["endpoint"],
                "method": test["method"],
                "data": test.get("data")
            })
    
    # Pad to exact number
    while len(requests_to_make) < num_requests:
        requests_to_make.append({
            "endpoint": "/health",
            "method": "GET"
        })
    
    results = []
    start_time = time.time()
    
    # Execute load test with thread pool
    with ThreadPoolExecutor(max_workers=concurrent_users) as executor:
        futures = [
            executor.submit(
                make_request,
                req["endpoint"],
                req["method"],
                False,
                req.get("data")
            )
            for req in requests_to_make
        ]
        
        completed = 0
        for future in as_completed(futures):
            result = future.result()
            results.append(result)
            completed += 1
            
            if completed % 10 == 0:
                print(f"Progress: {completed}/{num_requests} requests completed...")
    
    total_time = time.time() - start_time
    
    # Analyze results
    print("\n" + "="*80)
    print("LOAD TEST RESULTS")
    print("="*80)
    
    successful_requests = [r for r in results if r["success"]]
    failed_requests = [r for r in results if not r["success"]]
    
    response_times = [r["response_time_ms"] for r in successful_requests]
    
    print(f"\n📊 Overall Statistics:")
    print(f"   Total Requests: {len(results)}")
    print(f"   Successful: {len(successful_requests)} ({len(successful_requests)/len(results)*100:.1f}%)")
    print(f"   Failed: {len(failed_requests)} ({len(failed_requests)/len(results)*100:.1f}%)")
    print(f"   Total Time: {total_time:.2f} seconds")
    print(f"   Requests/Second: {len(results)/total_time:.2f}")
    
    if response_times:
        print(f"\n⏱️  Response Times:")
        print(f"   Average: {statistics.mean(response_times):.2f} ms")
        print(f"   Median: {statistics.median(response_times):.2f} ms")
        print(f"   Min: {min(response_times):.2f} ms")
        print(f"   Max: {max(response_times):.2f} ms")
        print(f"   Std Dev: {statistics.stdev(response_times):.2f} ms")
        
        # Percentiles
        sorted_times = sorted(response_times)
        p50 = sorted_times[int(len(sorted_times) * 0.50)]
        p95 = sorted_times[int(len(sorted_times) * 0.95)]
        p99 = sorted_times[int(len(sorted_times) * 0.99)]
        
        print(f"\n📈 Percentiles:")
        print(f"   P50: {p50:.2f} ms")
        print(f"   P95: {p95:.2f} ms")
        print(f"   P99: {p99:.2f} ms")
    
    # By endpoint
    print(f"\n🎯 Results by Endpoint:")
    endpoint_stats = {}
    for result in results:
        endpoint = result["endpoint"]
        if endpoint not in endpoint_stats:
            endpoint_stats[endpoint] = {
                "count": 0,
                "success": 0,
                "times": []
            }
        endpoint_stats[endpoint]["count"] += 1
        if result["success"]:
            endpoint_stats[endpoint]["success"] += 1
            endpoint_stats[endpoint]["times"].append(result["response_time_ms"])
    
    for endpoint, stats in sorted(endpoint_stats.items(), key=lambda x: x[1]["count"], reverse=True):
        success_rate = (stats["success"] / stats["count"]) * 100
        avg_time = statistics.mean(stats["times"]) if stats["times"] else 0
        print(f"   {endpoint:50} {stats['count']:3} req | {success_rate:5.1f}% success | {avg_time:6.1f}ms avg")
    
    # Status code distribution
    print(f"\n📊 Status Code Distribution:")
    status_codes = {}
    for result in results:
        code = result["status_code"]
        status_codes[code] = status_codes.get(code, 0) + 1
    
    for code, count in sorted(status_codes.items()):
        print(f"   {code}: {count} ({count/len(results)*100:.1f}%)")
    
    if failed_requests:
        print(f"\n❌ Failed Requests Sample:")
        for req in failed_requests[:5]:
            print(f"   {req['endpoint']}: {req.get('error', 'Unknown error')}")
    
    print("\n" + "="*80)
    print(f"✅ Load test complete! Check CloudWatch logs and dashboard for updated stats.")
    print("="*80)


if __name__ == "__main__":
    import sys
    
    num_requests = int(sys.argv[1]) if len(sys.argv) > 1 else 100
    concurrent_users = int(sys.argv[2]) if len(sys.argv) > 2 else 10
    
    print(f"\nStarting load test...")
    print(f"Tip: Use 'python load_test.py <num_requests> <concurrent_users>'")
    print(f"Example: python load_test.py 500 20\n")
    
    load_test(num_requests, concurrent_users)
