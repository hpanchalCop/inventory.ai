"""CloudWatch statistics service for API usage monitoring."""
import boto3
from botocore.exceptions import ClientError
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
from collections import defaultdict

from shared.config import settings


class CloudWatchStatsService:
    """Service for querying CloudWatch logs and metrics."""
    
    def __init__(self):
        """Initialize CloudWatch clients."""
        self.logs_client = None
        self.cloudwatch_client = None
        self._init_clients()
    
    def _init_clients(self):
        """Initialize AWS CloudWatch clients."""
        try:
            if settings.aws_access_key_id and settings.aws_secret_access_key:
                self.logs_client = boto3.client(
                    'logs',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
                self.cloudwatch_client = boto3.client(
                    'cloudwatch',
                    aws_access_key_id=settings.aws_access_key_id,
                    aws_secret_access_key=settings.aws_secret_access_key,
                    region_name=settings.aws_region
                )
            else:
                # Use default credentials (IAM role, environment, etc.)
                self.logs_client = boto3.client('logs', region_name=settings.aws_region)
                self.cloudwatch_client = boto3.client('cloudwatch', region_name=settings.aws_region)
            
            print("CloudWatch clients initialized")
        except Exception as e:
            print(f"Warning: Could not initialize CloudWatch clients: {e}")
    
    def get_request_stats_from_logs(
        self, 
        hours: int = 24
    ) -> Dict[str, Any]:
        """
        Query CloudWatch Logs Insights for API request statistics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with request statistics
        """
        if not self.logs_client:
            return self._get_mock_stats()
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query for request counts by endpoint
            # Matches uvicorn log format: INFO: IP:PORT - "METHOD /endpoint HTTP/1.1" STATUS
            query = """
            fields @timestamp, @message
            | filter @message like /"(GET|POST|DELETE|PUT|PATCH)/
            | parse @message /"(?<method>GET|POST|DELETE|PUT|PATCH) (?<endpoint>[^ ]+) HTTP/
            | stats count(*) as request_count by endpoint, method
            | sort request_count desc
            """
            
            response = self.logs_client.start_query(
                logGroupName=settings.cloudwatch_log_group,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query
            )
            
            query_id = response['queryId']
            
            # Wait for query to complete
            import time
            status = 'Running'
            while status in ['Running', 'Scheduled']:
                time.sleep(0.5)
                result = self.logs_client.get_query_results(queryId=query_id)
                status = result['status']
            
            if status == 'Complete':
                return self._parse_logs_insights_results(result['results'])
            else:
                print(f"Query failed with status: {status}")
                return self._get_mock_stats()
                
        except ClientError as e:
            print(f"CloudWatch Logs query error: {e}")
            return self._get_mock_stats()
        except Exception as e:
            print(f"Error querying CloudWatch: {e}")
            return self._get_mock_stats()
    
    def get_error_stats(self, hours: int = 24) -> Dict[str, Any]:
        """
        Query CloudWatch for error statistics.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with error statistics
        """
        if not self.logs_client:
            return {"error_count": 0, "error_rate": 0.0}
        
        try:
            end_time = datetime.utcnow()
            start_time = end_time - timedelta(hours=hours)
            
            # Query for errors (4xx and 5xx status codes)
            query = """
            fields @timestamp, @message
            | filter @message like /HTTP\\/[0-9.]+" (4|5)[0-9]{2}/
            | stats count(*) as error_count
            """
            
            response = self.logs_client.start_query(
                logGroupName=settings.cloudwatch_log_group,
                startTime=int(start_time.timestamp()),
                endTime=int(end_time.timestamp()),
                queryString=query
            )
            
            query_id = response['queryId']
            
            import time
            status = 'Running'
            while status in ['Running', 'Scheduled']:
                time.sleep(0.5)
                result = self.logs_client.get_query_results(queryId=query_id)
                status = result['status']
            
            if status == 'Complete' and result['results']:
                error_count = int(result['results'][0][0]['value']) if result['results'] else 0
                return {"error_count": error_count}
            
            return {"error_count": 0}
            
        except Exception as e:
            print(f"Error querying CloudWatch for errors: {e}")
            return {"error_count": 0}
    
    def get_response_time_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get response time metrics from CloudWatch Logs.
        
        Note: Uvicorn's default logging doesn't include response times.
        To track response times, custom middleware would need to be added.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dictionary with response time statistics (currently N/A)
        """
        return {
            "average_ms": "N/A",
            "max_ms": "N/A",
            "note": "Enable response time logging middleware to track metrics"
        }
    
    def get_full_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive API usage statistics.
        
        Returns:
            Dictionary with all statistics
        """
        # Get stats for different time periods
        stats_1h = self.get_request_stats_from_logs(hours=1)
        stats_24h = self.get_request_stats_from_logs(hours=24)
        stats_7d = self.get_request_stats_from_logs(hours=168)
        
        error_stats = self.get_error_stats(hours=24)
        response_times = self.get_response_time_metrics(hours=24)
        
        # Calculate error rate
        total_requests_24h = stats_24h.get('total_requests', 0)
        error_rate = (error_stats['error_count'] / total_requests_24h * 100) if total_requests_24h > 0 else 0
        
        return {
            "generated_at": datetime.utcnow().isoformat(),
            "total_requests": {
                "last_hour": stats_1h.get('total_requests', 0),
                "last_24_hours": stats_24h.get('total_requests', 0),
                "last_7_days": stats_7d.get('total_requests', 0)
            },
            "legitimate_requests": {
                "count": stats_24h.get('legitimate_count', 0),
                "by_endpoint": stats_24h.get('legitimate_endpoints', {})
            },
            "attack_attempts": {
                "count": stats_24h.get('attack_count', 0),
                "by_endpoint": dict(sorted(
                    stats_24h.get('attack_endpoints', {}).items(), 
                    key=lambda x: x[1], 
                    reverse=True
                )[:50])  # Limit to top 50 attack endpoints
            },
            "requests_by_endpoint": stats_24h.get('by_endpoint', {}),
            "requests_by_method": stats_24h.get('by_method', {}),
            "response_times": response_times,
            "errors": {
                "count_24h": error_stats['error_count'],
                "error_rate_percent": round(error_rate, 2)
            }
        }
    
    def _parse_logs_insights_results(self, results: List) -> Dict[str, Any]:
        """Parse CloudWatch Logs Insights query results and categorize endpoints."""
        by_endpoint = defaultdict(int)
        by_method = defaultdict(int)
        legitimate_endpoints = defaultdict(int)
        attack_endpoints = defaultdict(int)
        total = 0
        
        # Define legitimate endpoint patterns
        legitimate_patterns = [
            '/health', '/products', '/search', '/docs', '/openapi.json',
            '/_dash-', '/favicon.ico', '/admin/stats', '/'
        ]
        
        # Define attack patterns
        attack_patterns = [
            '.php', '.env', 'phpinfo', 'phpunit', 'eval-stdin',
            'config.php', '.git', '.aws', 'sftp', 'password.php',
            'vendor/', 'laravel/', 'wordpress/', 'wp-config',
            'XDEBUG', 'phpstorm', '_ignition', 'ReportServer',
            'boaform', 'setup.cgi', 'think\\app', 'cgi-bin'
        ]
        
        for row in results:
            endpoint = None
            method = None
            count = 0
            
            for field in row:
                if field['field'] == 'endpoint':
                    endpoint = field['value']
                elif field['field'] == 'method':
                    method = field['value']
                elif field['field'] == 'request_count':
                    count = int(field['value'])
            
            if endpoint:
                by_endpoint[endpoint] += count
                
                # Categorize endpoint
                is_attack = any(pattern in endpoint.lower() for pattern in attack_patterns)
                is_legitimate = any(endpoint.startswith(pattern) for pattern in legitimate_patterns)
                
                if is_attack:
                    attack_endpoints[endpoint] += count
                elif is_legitimate or endpoint in ['/', '/']:
                    legitimate_endpoints[endpoint] += count
                else:
                    # Unknown endpoints, treat as suspicious
                    attack_endpoints[endpoint] += count
                    
            if method:
                by_method[method] += count
            total += count
        
        return {
            'total_requests': total,
            'by_endpoint': dict(by_endpoint),
            'by_method': dict(by_method),
            'legitimate_endpoints': dict(legitimate_endpoints),
            'attack_endpoints': dict(attack_endpoints),
            'attack_count': sum(attack_endpoints.values()),
            'legitimate_count': sum(legitimate_endpoints.values())
        }
    
    def _get_mock_stats(self) -> Dict[str, Any]:
        """
        Return mock statistics when CloudWatch is not available.
        Useful for local development.
        """
        return {
            'total_requests': 0,
            'by_endpoint': {},
            'by_method': {},
            'note': 'CloudWatch not available - showing placeholder data. Deploy to AWS for real statistics.'
        }


# Singleton instance
cloudwatch_stats = CloudWatchStatsService()
