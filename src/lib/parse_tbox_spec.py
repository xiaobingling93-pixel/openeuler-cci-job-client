#!/usr/bin/env python3
# SPDX-License-Identifier: MulanPSL-2.0+
# Copyright (c) 2020 Huawei Technologies Co., Ltd. All rights reserved.

import os
import yaml
import requests
import time
import signal
import logging
from typing import Dict, Optional, List
from functools import wraps
from urllib.parse import urljoin

# Setup logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# Retry decorator for network requests
MAX_RETRIES = 3
RETRY_INTERVAL = 10  # seconds

# Environment variable names
LAB_REPO = "LAB_REPO"

# Default paths
DEFAULT_HOSTS_PATH = "/c/lab-z9"

# API base URL for machine operations (apply, query, cancel, return)
OPS_API_BASE = "https://localhost/api/v1/ops"

# Default values for dc/vm type
DEFAULT_DC_VM_PARAMS = {
    'nr_cpu': '2',
    'memory': '8G'
}

def retry_on_request_exception(func):
    """
    Decorator to retry a function on RequestException.
    Retries up to MAX_RETRIES times with RETRY_INTERVAL seconds between attempts.
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        last_exception = None
        for attempt in range(MAX_RETRIES):
            try:
                return func(*args, **kwargs)
            except requests.RequestException as e:
                last_exception = e
                if attempt < MAX_RETRIES - 1:
                    time.sleep(RETRY_INTERVAL)
        # After all retries failed, raise the last exception
        raise last_exception
    return wrapper

def parse_params(params_str: str) -> Dict[str, str]:
    """Parse comma-separated k=v pairs into dictionary."""
    if not params_str:
        return {}

    parsed = {}
    for pair in params_str.split(','):
        pair = pair.strip()
        if '=' in pair:
            key, value = pair.split('=', 1)
            parsed[key.strip()] = value.strip()
    return parsed

def get_host_files(dir_path: Optional[str] = None, prefix: Optional[str] = None) -> List[str]:
    """Get list of host files from directory, optionally filtered by prefix."""
    if dir_path is None:
        lab_repo = os.environ.get(LAB_REPO, DEFAULT_HOSTS_PATH)
        dir_path = os.path.join(lab_repo, 'hosts')

    if not os.path.isdir(dir_path):
        return []

    files = [f for f in os.listdir(dir_path)
            if os.path.isfile(os.path.join(dir_path, f))]

    if prefix is not None:
        files = [f for f in files if f.startswith(prefix)]

    return files

def match_host_file(filename: str, dir_path: Optional[str], params: Dict[str, str]) -> Optional[Dict]:
    """
    Check if a host file matches the given parameters.
    Returns the file content if matched, None otherwise.
    """
    if dir_path is None:
        lab_repo = os.environ.get(LAB_REPO, DEFAULT_HOSTS_PATH)
        dir_path = os.path.join(lab_repo, 'hosts')

    file_path = os.path.join(dir_path, filename)
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = yaml.safe_load(f)

        if not isinstance(content, dict):
            return None

        # Check if all specified parameters match
        for key, value in params.items():
            file_value = content.get(key)

            if file_value is None:
                return None

            # Handle memory matching - strip 'G' suffix and compare numbers
            if key == 'memory' and file_value and value:
                file_memory = str(file_value).rstrip('gG')
                param_memory = str(value).rstrip('gG')
                try:
                    if int(file_memory) != int(param_memory):
                        return None
                except ValueError:
                    return None
            else:
                # For other parameters, do exact string comparison
                if str(file_value) != str(value):
                    return None

        return content

    except Exception:
        return None

def get_dc_vm_testboxes(dir_path: Optional[str] = None, params: Optional[str] = None) -> List[Dict]:
    """
    Get testbox info for type=dc or type=vm.

    Args:
        dir_path: Directory containing testbox YAML files.
        params: Comma-separated k=v pairs with type, arch, model_name, nr_cpu, memory
                If nr_cpu/memory not specified, uses defaults: nr_cpu=2, memory=8G

    Returns:
        List of {testbox, type} dicts
    """
    parsed_params = parse_params(params) if params else {}

    # Get type - dc or vm
    tbox_type = parsed_params.get('type', '')
    if tbox_type not in ('dc', 'vm'):
        return []

    # Remove arch and type from params - these are not in yaml files
    parsed_params.pop('arch', None)
    parsed_params.pop('type', None)

    # Apply defaults if not specified
    if 'nr_cpu' not in parsed_params:
        parsed_params['nr_cpu'] = DEFAULT_DC_VM_PARAMS['nr_cpu']
    if 'memory' not in parsed_params:
        parsed_params['memory'] = DEFAULT_DC_VM_PARAMS['memory']

    # Determine directory to search
    if dir_path is None:
        lab_repo = os.environ.get(LAB_REPO, DEFAULT_HOSTS_PATH)
        dir_path = os.path.join(lab_repo, 'hosts')

    result = []

    # Filter by prefix: vm- for vm, dc- for dc
    prefix = f"{tbox_type}-"
    file_list = get_host_files(dir_path, prefix)

    for filename in file_list:
        content = match_host_file(filename, dir_path, parsed_params)

        if content:
            result.append({"testbox": filename, "type": tbox_type})

    return result

def poll_apply_task(task_id: int, api_key: str, api_url: Optional[str] = None, poll_interval: int = 2, duration: int = 86400) -> List[str]:
    """
    Poll for task completion and return available IPs.
    Handles SIGTERM signal to cancel the task gracefully.

    Args:
        task_id: Task ID to poll
        api_key: API key for authentication
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)
        poll_interval: Interval in seconds between polling
        duration: Maximum wait time in seconds (default: 86400)

    Returns:
        List of available IP addresses, empty list if interrupted or timeout
    """
    if api_url is None:
        api_url = OPS_API_BASE

    current_task_id = task_id
    current_api_key = api_key
    current_url_base = api_url
    interrupted = [False]
    start_time = time.time()

    def sigterm_handler(signum, frame):
        logger.info(f"Received SIGTERM, cancelling task {current_task_id}...")
        interrupted[0] = True
        try:
            cancel_apply_task(current_task_id, current_api_key, current_url_base)
            logger.info(f"Task {current_task_id} cancelled successfully.")
        except Exception as e:
            logger.info(f"Failed to cancel task {current_task_id}: {e}")

    original_handler = signal.signal(signal.SIGTERM, sigterm_handler)
    start_time = time.time()

    try:
        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed > duration:
                logger.info(f"Poll timeout after {elapsed:.0f} seconds, cancelling task...")
                try:
                    cancel_apply_task(current_task_id, current_api_key, current_url_base)
                    logger.info(f"Task {current_task_id} cancelled due to timeout.")
                except Exception as e:
                    logger.info(f"Failed to cancel task {current_task_id}: {e}")
                raise TimeoutError(f"Polling task {task_id} timed out after {duration} seconds")

            if interrupted[0]:
                logger.info("Poll loop cancelled by SIGTERM")
                return []

            try:
                task_data = query_apply_task(task_id, api_key, api_url)

                state = task_data.get('state', '')

                # Check if task is completed
                if state == 'completed':
                    schedule = task_data.get('schedule', {})
                    started_tasks = schedule.get('started_tasks', [])

                    if not started_tasks:
                        time.sleep(poll_interval)
                        continue

                    available_ips = []
                    for task_info in started_tasks:
                        if task_info.get('state') == 'complete':
                            available_ips.append(task_info.get('machine'))

                    if available_ips:
                        return available_ips
                    else:
                        time.sleep(poll_interval)

                elif state in ('failed', 'canceled'):
                    raise ValueError(f"Task failed or canceled: {state}")

                time.sleep(poll_interval)

            except Exception as e:
                raise ValueError(f"Failed to query task status: {e}")
    finally:
        signal.signal(signal.SIGTERM, original_handler)

def build_ip_filename_map(dir_path: Optional[str] = None, params: Optional[str] = None) -> Dict[str, str]:
    """
    Build IP to filename mapping from testbox files.
    Excludes vm- and dc- prefixed files.

    Args:
        dir_path: Directory containing testbox YAML files
        params: Matching parameters (comma-separated k=v)

    Returns:
        Dict mapping IP to filename
    """
    # Remove type from params if present
    hw_params = params
    if hw_params:
        parts = [p for p in hw_params.split(',') if not p.strip().startswith('type=')]
        hw_params = ','.join(parts)

    parsed_hw_params = parse_params(hw_params) if hw_params else {}

    # Build ip -> filename map (exclude vm- and dc- prefixes for hw)
    ip_filename_map = {}
    all_files = get_host_files(dir_path)
    file_list = [f for f in all_files if not f.startswith('vm-') and not f.startswith('dc-')]

    for filename in file_list:
        content = match_host_file(filename, dir_path, parsed_hw_params)
        if content:
            ip = content.get('ip')
            if ip:
                ip_filename_map[ip] = filename

    return ip_filename_map

def get_hw_testboxes(dir_path: Optional[str] = None, params: Optional[str] = None,
                     api_url: Optional[str] = None,
                     poll_interval: int = 2,
                     duration: int = 86400,
                     api_key: Optional[str] = None) -> List[Dict]:
    """
    Get available hw testboxes via API.

    Args:
        dir_path: Directory containing testbox YAML files
        params: Matching parameters (comma-separated k=v)
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)
        poll_interval: Interval in seconds between polling task status
        duration: Maximum wait time in seconds (default: 86400)
        api_key: API key for authentication

    Returns:
        List of {testbox, type, task_id, ip} dicts
    """
    # Build ip -> filename map
    ip_filename_map = build_ip_filename_map(dir_path, params)

    if not ip_filename_map:
        return []

    ip_list = list(ip_filename_map.keys())
    task_id = None

    # Use apply_machines function to create task
    try:
        task_id = apply_machines(ip_list, duration, api_key, api_url)
        if not task_id:
            raise ValueError(f"No task_id returned from apply")
    except Exception as e:
        raise ValueError(f"Failed to apply machines: {e}")

    # Poll for task completion
    try:
        available_ips = poll_apply_task(task_id, api_key, api_url, poll_interval, duration)

        # Get available IPs from started_tasks
        result_ips = available_ips

        if not result_ips:
            result_ips = ip_list

        # Build result: list of {testbox, type, task_id, ip} dicts
        result = []
        for ip in result_ips:
            if ip in ip_filename_map:
                filename = ip_filename_map[ip]
                result.append({"testbox": filename, "type": "hw", "task_id": task_id, "ip": ip})
            else:
                raise ValueError(f"IP {ip} from API not found in local testbox list")

        return result
    except Exception as e:
        # 发生异常时，尝试归还机器
        logger.info(f"Error occurred, returning machines: task_id={task_id}, ips={ip_list}")
        try:
            return_machines(ip_list, [task_id], api_key, api_url)
            logger.info(f"Machines returned successfully")
        except Exception as return_error:
            logger.info(f"Failed to return machines: {return_error}")
        raise e

def get_available_testboxes(dir_path: Optional[str] = None, params: Optional[str] = None,
                          api_url: Optional[str] = None,
                          poll_interval: int = 2,
                          num: int = 1,
                          duration: int = 86400,
                          api_key: Optional[str] = None) -> List[Dict]:
    """
    Get available testboxes by type.

    For type=dc or type=vm: returns list of YAML filenames
    For type=hw: calls API to get available testboxes, returns list of dicts

    Args:
        dir_path: Directory containing testbox YAML files
        params: Matching parameters (comma-separated k=v)
                Supports type=dc/vm/hw, and arch, model_name, nr_cpu, memory
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)
        poll_interval: Interval in seconds between polling task status
        num: Number of testboxes to request from API (for hw type)
        duration: Duration for machine apply in seconds (default: 86400)
        api_key: API key for authentication (required for hw type)

    Returns:
        For dc/vm: List of {testbox, type} dicts
        For hw: List of {testbox, type, task_id, ip} dicts
    """
    parsed_params = parse_params(params) if params else {}
    tbox_type = parsed_params.get('type', '')

    # Determine directory to search
    if dir_path is None:
        lab_repo = os.environ.get(LAB_REPO, DEFAULT_HOSTS_PATH)
        dir_path = os.path.join(lab_repo, 'hosts')

    # Handle dc/vm type - return filenames
    if tbox_type in ('dc', 'vm'):
        return get_dc_vm_testboxes(dir_path, params)

    # Handle hw type - use API to get available testboxes
    if tbox_type == 'hw' or tbox_type == '':
        return get_hw_testboxes(dir_path, params, api_url, poll_interval, duration, api_key)

    return []

@retry_on_request_exception
def apply_machines(ip_list: List[str], duration: int, api_key: str, api_url: Optional[str] = None) -> int:
    """
    Apply for machines.

    Args:
        ip_list: List of IP addresses to apply
        duration: Duration in seconds
        api_key: API key for authentication
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)

    Returns:
        Task ID (int)

    Raises:
        ValueError: If API call fails
    """
    if api_url is None:
        api_url = OPS_API_BASE

    url = urljoin(api_url.rstrip('/') + '/', "machines/apply")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    payload = {
        "ips": ip_list,
        "duration": f"{duration}s"
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    logger.info(f"Apply request: {response}, url: {url}, payload: {payload}")
    response.raise_for_status()
    data = response.json()

    if data.get('status') == 200:
        return data.get('data')
    else:
        raise ValueError(f"Apply failed: {data.get('error')}")

@retry_on_request_exception
def query_apply_task(task_id: int, api_key: str, api_url: Optional[str] = None) -> Dict:
    """
    Query apply task status.

    Args:
        task_id: Task ID returned from apply_machines
        api_key: API key for authentication
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)

    Returns:
        Task details dictionary

    Raises:
        ValueError: If API call fails
    """
    if api_url is None:
        api_url = OPS_API_BASE

    url = urljoin(api_url.rstrip('/') + '/', f"machines/apply/{task_id}")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    logger.info(f"Query task status URL: {url}")
    status_response = requests.get(url, headers=headers, timeout=30)
    status_response.raise_for_status()
    data = status_response.json()

    if data.get('status') == 200:
        return data.get('data', {})
    else:
        raise ValueError(f"Query failed: {data.get('error')}")

@retry_on_request_exception
def cancel_apply_task(task_id: int, api_key: str, api_url: Optional[str] = None) -> bool:
    """
    Cancel an apply task.

    Args:
        task_id: Task ID to cancel
        api_key: API key for authentication
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)

    Returns:
        True if cancelled successfully

    Raises:
        ValueError: If API call fails
    """
    if api_url is None:
        api_url = OPS_API_BASE

    url = urljoin(api_url.rstrip('/') + '/', f"machines/apply/{task_id}")
    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }

    response = requests.delete(url, headers=headers, timeout=30)
    response.raise_for_status()
    data = response.json()

    if data.get('status') == 200:
        return True
    else:
        raise ValueError(f"Cancel failed: {data.get('error')}")

@retry_on_request_exception
def return_machines(ip_list: List[str], task_ids: List[int], api_key: str, api_url: Optional[str] = None) -> Dict:
    """
    Return (release) machines.

    Args:
        ip_list: List of IP addresses to release
        task_ids: List of task IDs corresponding to the IPs
        api_key: API key for authentication
        api_url: Optional API URL prefix (if not provided, uses OPS_API_BASE)

    Returns:
        Dictionary with success_list, fail_list, etc.

    Raises:
        ValueError: If API call fails
    """
    if api_url is None:
        api_url = OPS_API_BASE

    url = urljoin(api_url.rstrip('/') + '/', f"machines/return")

    headers = {
        "x-api-key": api_key,
        "Content-Type": "application/json"
    }
    payload = {
        "ip_list": ip_list,
        "task_ids": task_ids
    }

    response = requests.post(url, json=payload, headers=headers, timeout=30)
    print(response, url, payload)
    response.raise_for_status()
    data = response.json()

    if data.get('status') == 200:
        return data.get('data', {})
    else:
        raise ValueError(f"Return failed: {data.get('error')}")

