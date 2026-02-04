#!/usr/bin/env python3
"""
wait_job_finish.py - 轮询 LKP 作业状态直到完成
"""

import sys
import time
import json
import argparse
import requests

from lib.constant import SCHED_HOST, SRV_HTTP_PORT, MAX_RETRIES, RETRY_DELAY


def print_step(step: str, message: str) -> None:
    """打印步骤信息"""
    print("=" * 60)
    print(f"{step}: {message}")
    print("=" * 60)


def die(msg: str) -> None:
    """输出错误并退出"""
    print(f"错误: {msg}", file=sys.stderr)
    sys.exit(1)


def fetch_job_status(
    job_id: str,
    sched_host: str,
    sched_port: int,
    fields: str = 'job_stage',
    timeout: int = 30
) -> tuple[dict, int]:
    """
    获取作业状态的网络请求方法。

    Args:
        job_id: 作业ID
        sched_host: 调度器主机
        sched_port: 调度器端口
        fields: 查询字段，默认为 'job_stage'
        timeout: 请求超时时间（秒），默认为30秒

    Returns:
        包含响应数据和状态码的元组 (data, status_code)

    Raises:
        requests.exceptions.RequestException: 网络请求异常
        json.JSONDecodeError: JSON解析异常
    """
    api_url = f"http://{sched_host}:{sched_port}/scheduler/v1/jobs/{job_id}?fields={fields}"
    resp = requests.get(api_url, timeout=timeout)
    data = resp.json() if resp.content else {}
    return data, resp.status_code

def wait_job_status(
    job_id: str,
    sched_host: str,
    sched_port: int,
    poll_interval: int = 10,
    timeout: int = 86400
) -> None:
    """
    轮询任务状态直到完成或中止。

    Args:
        job_id: 作业ID
        sched_host: 调度器主机
        sched_port: 调度器端口
        poll_interval: 轮询间隔（秒）
        timeout: 最长等待时间（秒），默认24小时（86400秒）
    """
    if not job_id:
        die("错误：未设置 job_id 变量")
    
    print_step("步骤1", f"轮询任务状态")
    
    # 初始化变量
    final_data = None
    final_stage = None
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            die(f"等待超时（{timeout}秒），任务仍未完成")
        try:
            data, status_code = fetch_job_status(job_id, sched_host, sched_port, fields='job_stage', timeout=30)
            if status_code != 200:
                print(f"警告：请求 API 失败（HTTP状态码：{status_code}），{poll_interval}秒后重试...")
                time.sleep(poll_interval)
                continue
            
            job_stage = data.get('job_stage')
            if job_stage is None:
                print(f"警告：无法解析任务状态，响应内容：{data}")
                time.sleep(poll_interval)
                continue
            
            print(f"当前任务状态：{job_stage}")
            
            # 判断是否终止
            if job_stage in ('finish', 'abort_invalid', 'abort_provider', 'abort_wait'):
                final_data = data
                final_stage = job_stage
                print(f"任务已终止，状态：{job_stage}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常：{e}，{poll_interval}秒后重试...")
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误：{e}，{poll_interval}秒后重试...")
        
        time.sleep(poll_interval)

    try:
        finish_data, finish_status_code = fetch_job_status(job_id, sched_host, sched_port, fields='job_health,result_root', timeout=30)
        if finish_status_code != 200:
            print(f"警告：请求 API 失败（HTTP状态码：{finish_status_code}）")

        job_health = finish_data.get('job_health')
        result_root = finish_data.get('result_root')
    except json.JSONDecodeError as e:
        print(f"JSON 解析错误：{e}，{poll_interval}秒后重试...")
    # 打印最终信息
    if final_stage and job_health and result_root:
        print(f"任务流程执行状态：job_stage = {final_stage}")
        print(f"任务用例测试状态：job_health = {job_health}")
        print(f"任务结果存放目录：result_root= {result_root}")

    if final_stage == 'finish':
        print("测试套执行结果归档链接：")
        print(f"http://{sched_host}:{SRV_HTTP_PORT}{result_root}")

    if final_stage == 'abort_invalid' or final_stage == 'abort_provider' or final_stage == 'abort_wait' or job_health != 'success':
        sys.exit(1)



def wait_job_finish(
    job_id: str,
    sched_host: str = '172.168.178.181',
    sched_port: int = 3000,
    poll_interval: int = 10,
    timeout: int = 86400
) -> None:
    """
    等待作业完成的主函数。
    
    Args:
        job_id: 作业ID
        sched_host: 调度器主机
        sched_port: 调度器端口
        poll_interval: 轮询间隔（秒）
        timeout: 最长等待时间（秒），默认24小时（86400秒）
    """
    wait_job_status(job_id, sched_host, sched_port, poll_interval, timeout)


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
        print("\n\n用户中断", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()