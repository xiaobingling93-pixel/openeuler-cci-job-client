#!/usr/bin/env python3
# -*- encoding=utf-8 -*-
"""
# **********************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2020-2020. All rights reserved.
# [openeuler-jenkins] is licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# Author:
# Create: 2026-03-06
# Description: 轮询 LKP 作业状态直到完成
# **********************************************************************************
"""

import sys
import time
import json
import os
import argparse
import requests
import subprocess
import logging.config

from pathlib import Path
from lib.constant import SRV_HTTP_PORT

if not logging.getLogger().hasHandlers():
    os.makedirs('logs', exist_ok=True)
    logger_config = os.path.join(str(Path(__file__).parent.parent), 'config', 'logger.conf')
    print(f"logger_config: {logger_config}")
    logging.config.fileConfig(logger_config, encoding="utf-8")

logger = logging.getLogger("common")

def print_step(step: str, message: str) -> None:
    """打印步骤信息"""
    logger.info("=" * 60)
    logger.info(f"{step}: {message}")
    logger.info("=" * 60)


def die(msg: str) -> None:
    """输出错误并退出"""
    logger.error(f"错误: {msg}")
    sys.exit(1)


def fetch_job_status(
    job_id: str,
    sched_host: str,
    sched_port: int,
    fields: str = None,
    timeout: int = 30
) -> tuple[dict, int]:
    """
    获取作业状态的网络请求方法。

    Args:
        job_id: 作业ID
        sched_host: 调度器主机
        sched_port: 调度器端口
        fields: 查询字段，默认为空
        timeout: 请求超时时间（秒），默认为30秒

    Returns:
        包含响应数据和状态码的元组 (data, status_code)

    Raises:
        requests.exceptions.RequestException: 网络请求异常
        json.JSONDecodeError: JSON解析异常
    """
    if fields:
        api_url = f"http://{sched_host}:{sched_port}/scheduler/v1/jobs/{job_id}?fields={fields}"
    else:
        api_url = f"http://{sched_host}:{sched_port}/scheduler/v1/jobs/{job_id}"
    resp = requests.get(api_url, timeout=timeout)
    data = resp.json() if resp.content else {}
    return data, resp.status_code

def query_jobs(job_id, sched_host, sched_port, timeout, poll_interval):
    start_time = time.time()
    job_stage = None
    pre_job_query_flag = False
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            die(f"等待超时（{timeout}秒），任务仍未完成")
        try:
            if pre_job_query_flag:
                data, status_code = fetch_job_status(job_id, sched_host, sched_port, fields="job_stage", timeout=30)
            else:
                data, status_code = fetch_job_status(job_id, sched_host, sched_port, timeout=30)
            if status_code != 200:
                logger.warning(f"警告：请求 API 失败（HTTP状态码：{status_code}），{poll_interval}秒后重试...")
                time.sleep(poll_interval)
                continue
            job_stage = data.get('job_stage')
            if not pre_job_query_flag:
                job_suite = data.get('suite')
                wait_job = data.get('wait_on')
                if wait_job:
                    pre_job_id = list(wait_job.keys())[0]
                    logger.info(f"{job_suite}:{job_id}存在前置任务{pre_job_id}, 需查询并等到前置任务结束")
                    _, pre_job_suite = query_jobs(pre_job_id, sched_host, sched_port, timeout, poll_interval)
                    result_data, _ = fetch_job_status(pre_job_id, sched_host, sched_port,
                                                                       fields='result_root', timeout=30)
                    result_root = result_data.get('result_root')
                    logger.info(f"{pre_job_suite}:{pre_job_id}执行结果归档链接：")
                    logger.info(f"http://{sched_host}:{SRV_HTTP_PORT}{result_root}")
                else:
                    logger.info(f"{job_suite}:{job_id}不存在前置任务")
                pre_job_query_flag = True

            logger.info(f"当前任务:{job_suite},任务id:{job_id},任务状态：{job_stage}")

            # 判断是否终止
            if job_stage in ('finish', 'abort_invalid', 'abort_provider', 'abort_wait'):
                logger.info(f"{job_suite}:{job_id}任务已结束，状态：{job_stage}")
                break

        except requests.exceptions.RequestException as e:
            logger.error(f"请求异常：{e}，{poll_interval}秒后重试...")
        except json.JSONDecodeError as e:
            logger.error(f"JSON 解析错误：{e}，{poll_interval}秒后重试...")

        time.sleep(poll_interval)
    return job_stage, job_suite

def wait_job_status(
    job_id: str,
    sched_host: str,
    sched_port: int,
    poll_interval: int = 10,
    timeout: int = 86400,
    logs_dir: str = None
) -> None:
    """
    轮询任务状态直到完成或中止。

    Args:
        job_id: 作业ID
        sched_host: 调度器主机
        sched_port: 调度器端口
        poll_interval: 轮询间隔（秒）
        timeout: 最长等待时间（秒），默认24小时（86400秒）
        logs_dir: 回传日志的目的目录
    """
    if not job_id:
        die("错误：未设置 job_id 变量")
    
    logger.info("轮询任务状态")
    final_stage, job_suite = query_jobs(job_id, sched_host, sched_port, timeout, poll_interval)

    try:
        finish_data, finish_status_code = fetch_job_status(job_id, sched_host, sched_port, fields='job_health,result_root', timeout=30)
        if finish_status_code != 200:
            logger.warning(f"警告：请求 API 失败（HTTP状态码：{finish_status_code}）")

        job_health = finish_data.get('job_health')
        result_root = finish_data.get('result_root')
    except json.JSONDecodeError as e:
        logger.error(f"JSON 解析错误：{e}，{poll_interval}秒后重试...")
    # 打印最终信息
    if final_stage and job_health and result_root:
        logger.info(f"{job_suite}任务流程执行状态：job_stage = {final_stage}")
        logger.info(f"{job_suite}任务用例测试状态：job_health = {job_health}")
        logger.info(f"{job_suite}任务结果存放目录：result_root= {result_root}")
        logger.info(f"{job_suite}测试套执行结果归档链接：")
        logger.info(f"http://{sched_host}:{SRV_HTTP_PORT}{result_root}")
        if logs_dir:
            logger.info(f"用例日志将从compass-ci:{sched_host}的/srv{result_root}回传到{logs_dir}")
            cmd = [ "rsync", "-avz", "--progress", f"root@{sched_host}:/srv{result_root}", f"{logs_dir}" ]
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                if result.returncode != 0:
                    logger.error(f"用例日志回传失败：{result.stdout.strip()}:{result.stderr}")
            except Exception as e:
                logger.error(f"用例日志回传出现异常：{e}")


    if final_stage == 'abort_invalid' or final_stage == 'abort_provider' or final_stage == 'abort_wait' or job_health != 'success':
        sys.exit(1)

def wait_job_finish(
    job_id: str,
    sched_host: str = '172.168.178.181',
    sched_port: int = 3000,
    poll_interval: int = 10,
    timeout: int = 86400,
    logs_dir: str = None
) -> None:
    """
    等待作业完成的主函数。
    
    Args:
        job_id: 作业ID
        sched_host: 调度器主机
        sched_port: 调度器端口
        poll_interval: 轮询间隔（秒）
        timeout: 最长等待时间（秒），默认24小时（86400秒）
        logs_dir: 回传日志的目的目录
    """
    wait_job_status(job_id, sched_host, sched_port, poll_interval, timeout, logs_dir)


def main():
    parser = argparse.ArgumentParser(
        description='轮询 LKP 作业状态直到完成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  %(prog)s --job_id 123456
  
  # 指定调度器地址和端口
  %(prog)s --job_id 123456 --sched_host 192.168.1.100 --sched_port 3000
  
  # 指定轮询间隔
  %(prog)s --job_id 123456 --poll_interval 5
  
  # 指定最长等待时间（例如2小时）
  %(prog)s --job_id 123456 --timeout 7200
        """
    )
    
    parser.add_argument('--job_id', required=True, help='作业ID（必需）')
    parser.add_argument('--sched_host', default='172.168.178.181', help='调度器主机 (默认: 172.168.178.181)')
    parser.add_argument('--sched_port', type=int, default=3000, help='调度器端口 (默认: 3000)')
    parser.add_argument('--poll_interval', type=int, default=10, help='轮询间隔（秒）(默认: 10)')
    parser.add_argument('--timeout', type=int, default=86400, help='最长等待时间（秒），默认24小时（86400秒）')
    
    args = parser.parse_args()
    
    try:
        wait_job_finish(
            job_id=args.job_id,
            sched_host=args.sched_host,
            sched_port=args.sched_port,
            poll_interval=args.poll_interval,
            timeout=args.timeout
        )
    except KeyboardInterrupt:
        logger.warning("\n\n用户中断", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        logger.error(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()