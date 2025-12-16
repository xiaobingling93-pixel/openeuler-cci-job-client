#!/usr/bin/env python3
"""
wait_job_finish.py - 轮询 LKP 作业状态直到完成
"""

import sys
import time
import json
import argparse
import requests


def print_step(step: str, message: str) -> None:
    """打印步骤信息"""
    print("=" * 60)
    print(f"{step}: {message}")
    print("=" * 60)


def die(msg: str) -> None:
    """输出错误并退出"""
    print(f"错误: {msg}", file=sys.stderr)
    sys.exit(1)


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
    
    api_url = f"http://{sched_host}:{sched_port}/scheduler/v1/jobs/{job_id}?fields=job_stage"
    print_step("步骤1", f"轮询任务状态，API: {api_url}")
    
    # 初始化变量
    final_data = None
    final_stage = None
    start_time = time.time()
    
    while True:
        elapsed = time.time() - start_time
        if elapsed > timeout:
            die(f"等待超时（{timeout}秒），任务仍未完成")
        try:
            resp = requests.get(api_url, timeout=30)
            if resp.status_code != 200:
                print(f"警告：请求 API 失败（HTTP状态码：{resp.status_code}），{poll_interval}秒后重试...")
                time.sleep(poll_interval)
                continue
            
            data = resp.json()
            job_stage = data.get('job_stage')
            if job_stage is None:
                print(f"警告：无法解析任务状态，响应内容：{data}")
                time.sleep(poll_interval)
                continue
            
            print(f"当前任务状态：{job_stage}")
            
            # 判断是否终止
            if job_stage in ('finish', 'abort_invalid', 'abort_provider'):
                final_data = data
                final_stage = job_stage
                print(f"任务已终止，状态：{job_stage}")
                break
                
        except requests.exceptions.RequestException as e:
            print(f"请求异常：{e}，{poll_interval}秒后重试...")
        except json.JSONDecodeError as e:
            print(f"JSON 解析错误：{e}，{poll_interval}秒后重试...")
        
        time.sleep(poll_interval)
    
    # 打印最终信息
    if final_stage and final_data:
        print(f"任务最终状态：{final_stage}")
        print(f"任务完整信息：{json.dumps(final_data, indent=2)}")


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