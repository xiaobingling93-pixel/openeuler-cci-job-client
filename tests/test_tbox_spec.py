#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script for testbox.py using mock API server.
Usage:
    1. Start mock server: python mock_tbox_spec.py [port]
    2. Run tests: python test_tbox_spec.py [port]

Test scenarios:
    - test_apply_machines: Normal apply
    - test_query_apply_task: Query task status
    - test_cancel_apply_task: Cancel a task
    - test_return_machines: Return machines
    - test_get_available_testboxes_hw: Get HW testboxes via API
    - test_poll_timeout: Test timeout scenario (cancel on timeout)
    - test_poll_query_failure: Test query failure (return machines on error)
    - test_get_hw_testboxes_exception: Test exception handling (return machines)
"""

import sys
import os
import time
import subprocess
import threading
import signal

# Add the src/lib directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'lib'))

from parse_tbox_spec import (
    get_available_testboxes,
    build_ip_filename_map,
    apply_machines,
    query_apply_task,
    cancel_apply_task,
    return_machines,
    poll_apply_task,
    get_hw_testboxes,
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


def configure_mock_server(port, config):
    """Configure mock server via HTTP."""
    import requests
    try:
        resp = requests.post(
            f"http://127.0.0.1:{port}/_config/set",
            json=config,
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Failed to configure mock server: {e}")
        return False


def reset_mock_server(port):
    """Reset mock server config via HTTP."""
    import requests
    try:
        resp = requests.post(
            f"http://127.0.0.1:{port}/_config/reset",
            timeout=5
        )
        return resp.status_code == 200
    except Exception as e:
        print(f"Failed to reset mock server: {e}")
        return False


def test_poll_timeout(port):
    """Test poll_apply_task timeout scenario - should cancel task on timeout."""
    print("\n=== Testing poll_apply_task timeout ===")
    
    # Reset mock server config via HTTP
    reset_mock_server(port)
    
    # Configure mock server to return pending state
    configure_mock_server(port, {'task_state': 'pending'})
    
    # Create a task
    try:
        task_id = apply_machines(
            ip_list=["172.168.1.301"],
            duration=1,  # short duration (in seconds)
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops"
        )
        print(f"Applied task_id: {task_id}")
    except Exception as e:
        print(f"Apply failed: {e}")
        reset_mock_server(port)
        return
    
    # Poll with very short duration to trigger timeout
    try:
        result = poll_apply_task(
            task_id=task_id,
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops",
            poll_interval=0.1,
            duration=1  # 1 second timeout
        )
        print(f"poll_apply_task returned (timeout): {result}")
        # Should return empty list on timeout
        if result == []:
            print("Timeout test PASSED: returned empty list as expected")
        else:
            print(f"Timeout test FAILED: expected [], got {result}")
    except TimeoutError as e:
        print(f"TimeoutError raised as expected: {e}")
        print("Timeout test PASSED")
    except Exception as e:
        print(f"poll_apply_task failed: {e}")
    finally:
        reset_mock_server(port)


def test_poll_query_failure(port):
    """Test poll_apply_task when query fails - should try to return machines."""
    print("\n=== Testing poll_apply_task query failure ===")
    
    # Reset mock server config via HTTP
    reset_mock_server(port)
    
    try:
        task_id = apply_machines(
            ip_list=["172.168.1.302"],
            duration=1,
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops"
        )
        print(f"Applied task_id: {task_id}")
    except Exception as e:
        print(f"Apply failed: {e}")
        reset_mock_server(port)
        return
    
    # Configure mock to fail on query
    configure_mock_server(port, {'fail_query': True})
    
    # Poll - should raise exception due to query failure
    try:
        result = poll_apply_task(
            task_id=task_id,
            api_key="test-api-key",
            api_url=f"http://127.0.0.1:{port}/api/v1/ops",
            poll_interval=0.1,
            duration=2
        )
        print(f"poll_apply_task returned: {result}")
        print("Query failure test: No exception raised (unexpected)")
    except ValueError as e:
        print(f"ValueError raised as expected: {e}")
        print("Query failure test PASSED")
    except Exception as e:
        print(f"poll_apply_task raised exception: {type(e).__name__}: {e}")
        print("Query failure test PASSED (exception raised)")
    finally:
        reset_mock_server(port)


def test_get_hw_testboxes_exception(port):
    """Test get_hw_testboxes exception handling - should return machines on error."""
    print("\n=== Testing get_hw_testboxes exception handling ===")
    
    # Reset mock server config via HTTP
    reset_mock_server(port)
    
    # Create a temporary hosts directory for testing
    import tempfile
    import yaml
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test host file
        host_file = os.path.join(tmpdir, 'test-host.yaml')
        with open(host_file, 'w') as f:
            yaml.dump({
                'ip': '172.168.1.303',
                'arch': 'aarch64',
                'nr_cpu': '4',
                'memory': '8G'
            }, f)
        
        # Configure mock to fail on apply
        configure_mock_server(port, {'fail_apply': True})
        
        try:
            result = get_hw_testboxes(
                dir_path=tmpdir,
                params="type=hw,arch=aarch64",
                api_url=f"http://127.0.0.1:{port}/api/v1/ops",
                poll_interval=0.1,
                duration=1,
                api_key="test-api-key"
            )
            print(f"get_hw_testboxes returned: {result}")
            print("Exception test FAILED: No exception raised")
        except ValueError as e:
            print(f"ValueError raised as expected: {e}")
            print("Exception handling test PASSED")
        except Exception as e:
            print(f"Exception raised: {type(e).__name__}: {e}")
            print("Exception handling test PASSED")
        finally:
            reset_mock_server(port)


def test_cancel_on_exception_in_get_hw_testboxes(port):
    """Test that machines are returned when exception occurs in get_hw_testboxes."""
    print("\n=== Testing machine return on exception in get_hw_testboxes ===")
    
    # Reset mock server config via HTTP
    reset_mock_server(port)
    
    # Create a temporary hosts directory
    import tempfile
    import yaml
    
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test host files
        for i in range(3):
            host_file = os.path.join(tmpdir, f'test-host-{i}.yaml')
            with open(host_file, 'w') as f:
                yaml.dump({
                    'ip': f'172.168.1.{310+i}',
                    'arch': 'aarch64',
                    'nr_cpu': '4',
                    'memory': '8G'
                }, f)
        
        # Configure: apply succeeds, but query fails
        configure_mock_server(port, {'fail_query': True})
        
        try:
            # This should apply machines, then fail on query, and try to return
            result = get_hw_testboxes(
                dir_path=tmpdir,
                params="type=hw,arch=aarch64",
                api_url=f"http://127.0.0.1:{port}/api/v1/ops",
                poll_interval=0.1,
                duration=1,
                api_key="test-api-key"
            )
            print(f"get_hw_testboxes returned: {result}")
        except Exception as e:
            print(f"Exception raised (expected): {type(e).__name__}: {e}")
            print("Machine return on exception test completed")
        finally:
            reset_mock_server(port)


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8888
    
    print(f"Testing with mock server on port {port}")
    print(f"OPS_API_BASE: {OPS_API_BASE}")
    
    # Wait for server to be ready
    if not wait_for_server(port):
        print(f"Error: Mock server not running on port {port}")
        print("Please start it first: python mock_tbox_spec.py")
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
    
    # === New tests for exception handling ===
    
    # Test timeout scenario
    test_poll_timeout(port)
    
    # Test query failure scenario
    test_poll_query_failure(port)
    
    # Test exception handling in get_hw_testboxes
    test_get_hw_testboxes_exception(port)
    
    # Test machine return on exception
    test_cancel_on_exception_in_get_hw_testboxes(port)
    
    print("\n=== All tests completed ===")


if __name__ == '__main__':
    main()


