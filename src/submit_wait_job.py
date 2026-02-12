#!/usr/bin/env python3
"""
submit_wait_job.py - 提交 LKP 作业并等待其完成

组合 submit_job.py 和 wait_job_finish.py 的功能：
1. 提交作业并获取 job_id
2. 轮询作业状态直到完成或超时
"""

import sys
import argparse
import time

from submit_job import submit_job
from wait_job_finish import wait_job_finish
from lib.constant import (
    OS_NAME,
    OS_ARCH,
    OS_VERSION,
    TESTBOX,
    MY_ACCOUNT,
    MY_NAME,
    MY_TOKEN,
    MY_EMAIL,
    JOB_YAML,
    SCHED_PORT,
    SCHED_HOST,
)
from lib.parse_params_utils import parse_extra_params


def print_step(step: str, message: str) -> None:
    """打印步骤信息"""
    print("=" * 60)
    print(f"{step}: {message}")
    print("=" * 60)




def main():
    parser = argparse.ArgumentParser(
        description='提交 LKP 作业并等待其完成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  %(prog)s --my_account real_account --my_token real_token

  # 指定所有参数
  %(prog)s \\
    --os openeuler \\
    --os_arch aarch64 \\
    --os_version 24.03-LTS \\
    --testbox vm-2p8g \\
    --my_account my_account \\
    --my_name my_name \\
    --my_token my_token \\
    --my_email my_email@qq.com \\
    --job_yaml host-info.yaml \\
    --sched_host 172.168.178.181 \\
    --sched_port 3000 \\
    --poll_interval 10 \\
    --timeout 86400

  # 使用额外参数（多种方式）
  %(prog)s --extra kernel=linux-5.10 --extra memory=8G --extra cpu=4
  %(prog)s --extra "kernel=linux-5.10 memory=8G cpu=4"

  # 跳过 LKP 客户端准备
  %(prog)s --skip_prepare

  # 快速轮询
  %(prog)s --poll_interval 5 --timeout 3600
        """
    )

    # submit_job 参数
    parser.add_argument('--os', default=OS_NAME, help='操作系统名称 (默认: openeuler)')
    parser.add_argument('--os_arch', default=OS_ARCH, help='操作系统架构 (默认: aarch64)')
    parser.add_argument('--os_version', default=OS_VERSION, help='操作系统版本 (默认: 24.03-LTS)')
    parser.add_argument('--testbox', default=TESTBOX, help='测试机类型 (默认: vm-2p8g)')
    parser.add_argument('--my_account', default=MY_ACCOUNT, help='账户 (默认: my_account)')
    parser.add_argument('--my_name', default=MY_NAME, help='姓名 (默认: my_name)')
    parser.add_argument('--my_token', default=MY_TOKEN, help='令牌 (默认: my_token)')
    parser.add_argument('--my_email', default=MY_EMAIL, help='邮箱 (默认: my_email@qq.com)')
    parser.add_argument('--job_yaml', default=JOB_YAML, help='作业 YAML 文件 (默认: host-info.yaml)')
    parser.add_argument('--sched_port', type=int, default=SCHED_PORT, help='调度器端口 (默认: 3000)')
    parser.add_argument('--sched_host', default=SCHED_HOST, help='调度器主机 (默认: 172.168.178.181)')
    parser.add_argument('--skip_prepare', action='store_true', help='跳过 LKP 客户端准备')
    parser.add_argument('--extra', action='append', default=[], help='额外的键值对参数，格式为 key=value 可重复使用，支持空格分隔多个键值对')

    # wait_job_finish 参数
    parser.add_argument('--poll_interval', type=int, default=10, help='轮询间隔（秒）(默认: 10)')
    parser.add_argument('--timeout', type=int, default=86400, help='最长等待时间（秒），默认24小时（86400秒）')
    parser.add_argument("--logs_dir", help='指定这个参数后，用例执行完的日志会从compass-ci服务器回传到该目录下')

    args = parser.parse_args()

    try:
        # 步骤1：提交作业
        print_step("步骤1", "提交 LKP 作业")
        # 解析 extra 参数
        extra_params = parse_extra_params(args.extra) if args.extra else None
        print(f"the extra params: {extra_params}")
        
        job_id = submit_job(
            os_name=args.os,
            os_arch=args.os_arch,
            os_version=args.os_version,
            testbox=args.testbox,
            my_account=args.my_account,
            my_name=args.my_name,
            my_token=args.my_token,
            my_email=args.my_email,
            job_yaml=args.job_yaml,
            sched_port=args.sched_port,
            sched_host=args.sched_host,
            skip_prepare=args.skip_prepare,
            extra_params=extra_params
        )
        print(f"作业提交成功，job_id = {job_id}")

        # 步骤2：等待作业完成
        print_step("步骤4", f"等待作业 {job_id} 完成")
        wait_job_finish(
            job_id=job_id,
            sched_host=args.sched_host,
            sched_port=args.sched_port,
            poll_interval=args.poll_interval,
            timeout=args.timeout,
            logs_dir=args.logs_dir
        )

        print_step("完成", "作业处理完毕")
        sys.exit(0)

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