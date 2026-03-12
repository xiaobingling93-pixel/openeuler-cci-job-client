#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Mock test server for testing testbox.py API functions.
Simulates the OPS API endpoints without requiring real network access.
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
        
        # Parse path
        path = urlparse(self.path).path
        
        if path == '/api/v1/ops/machines/apply':
            # Mock apply_machines
            try:
                data = json.loads(body)
            except json.JSONDecodeError:
                data = {}
            
            ip_list = data.get('ip_list', [])
            duration = data.get('duration', '24h')
            
            # Create mock task
            task_id = mock_task_id_counter
            mock_task_id_counter += 1
            
            mock_tasks[task_id] = {
                'state': 'pending',
                'schedule': {'started_tasks': []},
                'ip_list': ip_list,
                'duration': duration
            }
            
            # Simulate async task completion
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
        path = urlparse(self.path).path
        
        # Extract task_id from path
        parts = path.rstrip('/').split('/')
        
        if len(parts) > 0 and parts[-1].isdigit():
            task_id = int(parts[-1])
            
            if path.startswith('/api/v1/ops/machines/apply/'):
                # Mock query_apply_task
                if task_id in mock_tasks:
                    self._send_json_response(200, {'status': 200, 'data': mock_tasks[task_id]})
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
            # Mark task as completed
            mock_tasks[task_id]['state'] = 'completed'
            
            # Add started tasks with complete state
            started_tasks = []
            for ip in ip_list:
                started_tasks.append({
                    'machine': ip,
                    'state': 'complete'
                })
            
            mock_tasks[task_id]['schedule']['started_tasks'] = started_tasks


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

