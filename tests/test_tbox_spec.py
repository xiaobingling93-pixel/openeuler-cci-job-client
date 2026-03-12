#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for testbox.py using mock API server.
Usage:
    1. Start mock server: python tt.py [port]
    2. Run tests: python test_tt.py [port]
"""

import sys
import os
import time
import subprocess
import threading

# Add the src/lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'lib'))

from parse_tbox_spec import (
    get_available_testboxes,
    build_ip_filename_map,
    apply_machines,
    query_apply_task,
    cancel_apply_task,
    return_machines,
    OPS_API_BASE
)


def wait_for_server(port, max_attempts=10):
    """Wait for mock server to start."""
    import socket
    for _ in range(max_attempts):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            if result == 0:
                return True
        except:
            pass
        time.sleep(0.5)
    return False


def test_apply_machines(port):
    """Test apply_machines function."""
    print("\n=== Testing apply_machines ===")
    try:
        task_id = apply_machines(
            ip_list=["172.168.1.101", "172.168.1.102"],
            duration="24h",
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops"
        )
        print(f"apply_machines succeeded, task_id: {task_id}")
        return task_id
    except Exception as e:
        print(f"apply_machines failed: {e}")
        return None


def test_query_apply_task(port, task_id):
    """Test query_apply_task function."""
    print("\n=== Testing query_apply_task ===")
    try:
        # Wait a bit for async task to complete
        time.sleep(1)
        
        task_data = query_apply_task(
            task_id=task_id,
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops"
        )
        print(f"query_apply_task succeeded, state: {task_data.get('state')}")
        return task_data
    except Exception as e:
        print(f"query_apply_task failed: {e}")
        return None


def test_cancel_apply_task(port, task_id):
    """Test cancel_apply_task function."""
    print("\n=== Testing cancel_apply_task ===")
    # First create a new task
    new_task_id = apply_machines(
        ip_list=["172.168.1.201"],
        duration="24h",
        api_key="test-api-key",
        api_url=f"http://127.0.0.1:{port}/api/v1/ops"
    )
    
    try:
        result = cancel_apply_task(
            task_id=new_task_id,
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops"
        )
        print(f"cancel_apply_task succeeded, result: {result}")
        return result
    except Exception as e:
        print(f"cancel_apply_task failed: {e}")
        return None


def test_return_machines(port):
    """Test return_machines function."""
    print("\n=== Testing return_machines ===")
    try:
        result = return_machines(
            ip_list=["172.168.1.101", "172.168.1.102"],
            task_ids=[1, 2],
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops"
        )
        print(f"return_machines succeeded: {result}")
        return result
    except Exception as e:
        print(f"return_machines failed: {e}")
        return None


def test_get_available_testboxes_hw(port):
    """Test get_available_testboxes for hw type."""
    print("\n=== Testing get_available_testboxes (hw) ===")
    try:
        result = get_available_testboxes(
            dir_path=None,  # Will use default
            params="type=hw,arch=aarch64",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops",
            num=2
        )
        print(f"get_available_testboxes (hw) succeeded: {result}")
        return result
    except Exception as e:
        print(f"get_available_testboxes (hw) failed: {e}")
        return None


def test_build_ip_filename_map():
    """Test build_ip_filename_map function."""
    print("\n=== Testing build_ip_filename_map ===")
    try:
        result = build_ip_filename_map(
            dir_path=None,  # Will use default
            params="arch=aarch64"
        )
        print(f"build_ip_filename_map succeeded: {result}")
        return result
    except Exception as e:
        print(f"build_ip_filename_map failed: {e}")
        return None


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    
    print(f"Testing with mock server on port {port}")
    print(f"OPS_API_BASE: {OPS_API_BASE}")
    
    # Wait for server to be ready
    if not wait_for_server(port):
        print(f"Error: Mock server not running on port {port}")
        print("Please start it first: python tt.py")
        sys.exit(1)
    
    print("Connected to mock server")
    
    # Test apply_machines
    task_id = test_apply_machines(port)
    
    # Test query_apply_task
    if task_id:
        test_query_apply_task(port, task_id)
    
    # Test cancel_apply_task
    test_cancel_apply_task(port, task_id or 1)
    
    # Test return_machines
    test_return_machines(port)
    
    # Test build_ip_filename_map (doesn't need API)
    test_build_ip_filename_map()
    
    # Test get_available_testboxes with hw (requires API)
    test_get_available_testboxes_hw(port)
    
    print("\n=== All tests completed ===")


if __name__ == '__main__':
    main()

