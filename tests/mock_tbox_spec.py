#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock test server for testing testbox.py API functions.
Simulates the OPS API endpoints without requiring real network access.

Supports different scenarios via query parameters:
- /api/v1/ops/machines/apply?fail=true - to simulate apply failure
- /api/v1/ops/machines/apply/{id}?fail=true - to simulate query failure
- /api/v1/ops/machines/apply/{id}?delay=X - to delay response by X seconds
- /api/v1/ops/machines/apply/{id}?never_complete=true - to never complete the task
"""

import json
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import threading
import sys


# Mock data storage
mock_tasks = {}
mock_task_id_counter = 1

# Configuration for test scenarios
config = {
    'fail_apply': False,
    'fail_query': False,
    'query_delay': 0,
    'never_complete': False,
    'task_state': 'completed'  # can be 'completed', 'failed', 'pending'
}


def reset_config():
    """Reset all configuration to defaults."""
    config['fail_apply'] = False
    config['fail_query'] = False
    config['query_delay'] = 0
    config['never_complete'] = False
    config['task_state'] = 'completed'


class MockAPIHandler(BaseHTTPRequestHandler):
    """Mock API request handler."""
    
    def log_message(self, format, *args):
        """Suppress default logging."""
        pass
    
    def _send_json_response(self, status_code, data):
        """Send JSON response."""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())
    
    def do_POST(self):
        """Handle POST requests."""
        global mock_task_id_counter
        
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
        
        # Parse path and query
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        if path == '/api/v1/ops/machines/apply':
            # Check if we should fail
            if query.get('fail', ['false'])[0] == 'true' or config['fail_apply']:
                self._send_json_response(500, {'status': 500, 'error': 'Internal server error'})
                return
            
            # Mock apply_machines
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            
            # Support both 'ips' and 'ip_list' keys
            ip_list = data.get('ips', data.get('ip_list', []))
            duration = data.get('duration', '24h')
            
            # Create mock task
            task_id = mock_task_id_counter
            mock_task_id_counter += 1
            
            # Check if task should never complete
            never_complete = query.get('never_complete', ['false'])[0] == 'true' or config['never_complete']
            
            mock_tasks[task_id] = {
                'state': 'pending',
                'schedule': {'started_tasks': []},
                'ip_list': ip_list,
                'duration': duration,
                'never_complete': never_complete
            }
            
            # Simulate async task completion (only if not never_complete)
            if not never_complete:
                threading.Thread(target=self._simulate_task_completion, args=(task_id, ip_list)).start()
            
            self._send_json_response(200, {
                'status': 200,
                'data': task_id
            })
            
        elif path == '/api/v1/ops/machines/return':
            # Mock return_machines
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            
            ip_list = data.get('ip_list', [])
            task_ids = data.get('task_ids', [])
            
            success_list = ip_list[:]
            fail_list = []
            
            self._send_json_response(200, {
                'status': 200,
                'data': {
                    'success_list': success_list,
                    'fail_list': fail_list
                }
            })
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def do_GET(self):
        """Handle GET requests."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        query = parse_qs(parsed_url.query)
        
        # Extract task_id from path
        parts = path.rstrip('/').split('/')
        
        if len(parts) > 0 and parts[-1].isdigit():
            task_id = int(parts[-1])
            
            if path.startswith('/api/v1/ops/machines/apply/'):
                # Check if we should fail
                if query.get('fail', ['false'])[0] == 'true' or config['fail_query']:
                    self._send_json_response(500, {'status': 500, 'error': 'Query failed'})
                    return
                
                # Check if we should delay
                delay = float(query.get('delay', [0])[0])
                if delay > 0:
                    time.sleep(delay)
                
                # Mock query_apply_task
                if task_id in mock_tasks:
                    task_data = mock_tasks[task_id].copy()
                    # Allow overriding state via config
                    if config['task_state'] != 'completed':
                        task_data['state'] = config['task_state']
                    self._send_json_response(200, {'status': 200, 'data': task_data})
                else:
                    self._send_json_response(404, {'error': 'Task not found'})
            else:
                self._send_json_response(404, {'error': 'Not found'})
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def do_DELETE(self):
        """Handle DELETE requests."""
        path = urlparse(self.path).path
        
        # Extract task_id from path
        parts = path.rstrip('/').split('/')
        
        if len(parts) > 0 and parts[-1].isdigit():
            task_id = int(parts[-1])
            
            if path.startswith('/api/v1/ops/machines/apply/'):
                # Mock cancel_apply_task
                if task_id in mock_tasks:
                    mock_tasks[task_id]['state'] = 'canceled'
                    self._send_json_response(200, {'status': 200})
                else:
                    self._send_json_response(404, {'error': 'Task not found'})
            else:
                self._send_json_response(404, {'error': 'Not found'})
        else:
            self._send_json_response(404, {'error': 'Not found'})
    
    def _simulate_task_completion(self, task_id, ip_list):
        """Simulate async task completion."""
        time.sleep(0.5)  # Wait a bit
        
        if task_id in mock_tasks:
            task = mock_tasks[task_id]
            # Check if task was set to never_complete
            if task.get('never_complete', False):
                return
            
            # Mark task as completed
            task['state'] = 'completed'
            
            # Add started tasks with complete state
            started_tasks = []
            for ip in ip_list:
                started_tasks.append({
                    'machine': ip,
                    'state': 'complete'
                })
            
            task['schedule']['started_tasks'] = started_tasks


class MockServerController:
    """Controller for managing mock server scenarios."""
    
    @staticmethod
    def set_fail_apply(fail: bool):
        """Set apply to fail."""
        config['fail_apply'] = fail
    
    @staticmethod
    def set_fail_query(fail: bool):
        """Set query to fail."""
        config['fail_query'] = fail
    
    @staticmethod
    def set_query_delay(delay: float):
        """Set query delay in seconds."""
        config['query_delay'] = delay
    
    @staticmethod
    def set_never_complete(never: bool):
        """Set task to never complete."""
        config['never_complete'] = never
    
    @staticmethod
    def set_task_state(state: str):
        """Set task state (completed, failed, pending)."""
        config['task_state'] = state
    
    @staticmethod
    def reset():
        """Reset all configuration."""
        reset_config()
    
    @staticmethod
    def get_config():
        """Get current configuration."""
        return config.copy()


# Add HTTP endpoints for configuration to the handler
def _add_config_endpoints():
    """Add configuration endpoints to MockAPIHandler."""
    
    original_do_POST = MockAPIHandler.do_POST
    original_do_GET = MockAPIHandler.do_GET
    
    def new_do_POST(self):
        """Handle POST requests including config commands."""
        parsed_url = urlparse(self.path)
        path = parsed_url.path
        
        # Handle config endpoints
        if path == '/_config/reset':
            reset_config()
            self._send_json_response(200, {'status': 200, 'message': 'Config reset'})
            return
        elif path == '/_config/set':
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length).decode() if content_length > 0 else '{}'
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            
            if 'fail_apply' in data:
                config['fail_apply'] = data['fail_apply']
            if 'fail_query' in data:
                config['fail_query'] = data['fail_query']
            if 'query_delay' in data:
                config['query_delay'] = data['query_delay']
            if 'never_complete' in data:
                config['never_complete'] = data['never_complete']
            if 'task_state' in data:
                config['task_state'] = data['task_state']
            
            self._send_json_response(200, {'status': 200, 'config': config})
            return
        elif path == '/_config/get':
            self._send_json_response(200, {'status': 200, 'config': config})
            return
        
        # Call original handler for other POST requests
        return original_do_POST(self)
    
    MockAPIHandler.do_POST = new_do_POST

_add_config_endpoints()


def start_mock_server(port=8888):
    """Start the mock server."""
    server = HTTPServer(('127.0.0.1', port), MockAPIHandler)
    print(f"Mock API server running on http://127.0.0.1:{port}")
    print("Press Ctrl+C to stop")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping server...")
        server.shutdown()


if __name__ == '__main__':
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    start_mock_server(port)


