#!/usr/bin/env python3
"""
submit_job.py - 提交 LKP 作业并返回 job_id
"""

import sys
import os
import subprocess
import re
import argparse
from pathlib import Path
from typing import Optional, List
from lib.constant import (
    CCI_REPOS,
    LKP_SRC_PATH,
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


def print_step(step: str, message: str) -> None:
    """打印步骤信息"""
    print("=" * 60)
    print(f"{step}: {message}")
    print("=" * 60)


def die(msg: str) -> None:
    """输出错误并退出"""
    print(f"错误: {msg}", file=sys.stderr)
    sys.exit(1)




def prepare_lkp_client(cci_repos: str = CCI_REPOS) -> Path:
    """
    克隆 LKP 客户端仓库，返回 LKP_SRC 路径。
    """
    print_step("步骤2", "准备 LKP 客户端环境")
    
    cci_path = Path(cci_repos)
    cci_path.mkdir(parents=True, exist_ok=True)
    os.chdir(cci_path)
    
    
    # 克隆 lkp-tests
    lkp_tests_path = cci_path / "lkp-tests"
    if not lkp_tests_path.exists():
        print("克隆 lkp-tests 仓库...")
        result = subprocess.run(
            ['git', 'clone', 'https://gitee.com/compass-ci/lkp-tests.git'],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            die(f"克隆 lkp-tests git 仓库失败: {result.stderr}")
    else:
        print("lkp-tests 已存在，跳过克隆")
    
    lkp_src = lkp_tests_path
    print(f"LKP_SRC 路径为 {lkp_src}")
    return lkp_src


def submit_one_yaml(
    lkp_src: Path,
    job_yaml: str,
    testbox: str,
    os_name: str,
    os_arch: str,
    os_version: str,
    my_account: str,
    my_name: str,
    my_token: str,
    my_email: str,
    sched_host: str,
    sched_port: int,
    extra_params: Optional[List[str]] = None
) -> str:
    """
    提交一个 YAML 作业，返回提交输出。

    Args:
        extra_params: 额外的键值对参数列表，格式为 "key=value"
    """
    print_step("步骤3", f"提交作业 {job_yaml}")
    
    if not testbox:
        die("未找到 testbox 变量")
    
    # 构建命令行参数（key=value 形式）
    params = [
        f"os={os_name}",
        f"os_arch={os_arch}",
        f"os_version={os_version}",
        f"testbox={testbox}",
        f"my_account={my_account}",
        f"my_name={my_name}",
        f"my_token={my_token}",
        f"my_email={my_email}",
        f"SCHED_HOST={sched_host}",
        f"SCHED_PORT={sched_port}",
    ]
    # 添加额外参数
    if extra_params:
        params.extend(extra_params)
    
    # 打印参数以便调试
    print("命令行参数:")
    for param in params:
        # 隐藏 token 的完整值
        if param.startswith("my_token="):
            print(f"  my_token=****")
        else:
            print(f"  {param}")
    
    # 执行提交命令
    submit_cmd = lkp_src / "sbin" / "submit"
    if not submit_cmd.exists():
        die(f"提交命令不存在: {submit_cmd}")
    
    cmd = [str(submit_cmd)] + params + [job_yaml]
    print(f"执行命令: {' '.join(cmd)}")
    print(f"工作目录: {os.getcwd()}")
    
    # 仍然需要 LKP_SRC 环境变量，因为 submit 脚本可能依赖它
    env = os.environ.copy()
    env['LKP_SRC'] = str(lkp_src)
    
    result = subprocess.run(
        cmd,
        env=env,
        capture_output=True,
        text=True
    )
    
    out = result.stdout.strip()
    if result.returncode != 0:
        die(f"提交失败: {result.stderr}")
    
    print(f"提交后返回的信息: {out}")
    return out


def get_job_id(submit_output: str) -> str:
    """
    从提交输出中提取 job_id。
    """
    # 正则匹配 "got job id=xxx"
    pattern = r'got\s+job\s+id=([^,\s]+)'
    match = re.search(pattern, submit_output)
    if match:
        job_id = match.group(1)
    else:
        # 备用匹配
        lines = submit_output.split('\n')
        for line in lines:
            if 'got job id=' in line:
                job_id = line.split('got job id=')[1].split()[0].rstrip(',')
                break
        else:
            job_id = ""
    
    if not job_id:
        die("提交任务失败，未找到 job_id")
    
    print(f"提交任务成功，job id = {job_id}")
    return job_id


def submit_job(
    os_name: str = OS_NAME,
    os_arch: str = OS_ARCH,
    os_version: str = OS_VERSION,
    testbox: str = TESTBOX,
    my_account: str = MY_ACCOUNT,
    my_name: str = MY_NAME,
    my_token: str = MY_TOKEN,
    my_email: str = MY_EMAIL,
    job_yaml: str = JOB_YAML,
    sched_port: int = SCHED_PORT,
    sched_host: str = SCHED_HOST,
    skip_prepare: bool = False,
    extra_params: Optional[List[str]] = None
) -> str:
    """
    提交 LKP 作业并返回 job_id。
    
    Args:
        os_name: 操作系统名称
        os_arch: 操作系统架构
        os_version: 操作系统版本
        testbox: 测试机类型
        my_account: 账户
        my_name: 姓名
        my_token: 令牌
        my_email: 邮箱
        job_yaml: 作业 YAML 文件
        sched_port: 调度器端口
        sched_host: 调度器主机
        skip_prepare: 跳过 LKP 客户端准备
        extra_params: 额外的键值对参数列表，格式为 "key=value"
    
    Returns:
        job_id: 提交后得到的作业ID
    """
    
    # 准备 LKP 客户端
    if not skip_prepare:
        lkp_src = prepare_lkp_client()
    
    lkp_src = LKP_SRC_PATH
    
    # 提交作业
    output = submit_one_yaml(
        lkp_src=lkp_src,
        job_yaml=job_yaml,
        testbox=testbox,
        os_name=os_name,
        os_arch=os_arch,
        os_version=os_version,
        my_account=my_account,
        my_name=my_name,
        my_token=my_token,
        my_email=my_email,
        sched_host=sched_host,
        sched_port=sched_port,
        extra_params=extra_params
    )
    
    # 提取 job_id
    job_id = get_job_id(output)
    return job_id


def main():
    parser = argparse.ArgumentParser(
        description='提交 LKP 作业并返回 job_id',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 基本用法
  %(prog)s --os openeuler --os_arch aarch64 --os_version 24.03-LTS
  
  # 指定测试机类型
  %(prog)s --testbox vm-4p16g
  
  # 跳过客户端准备
  %(prog)s --skip-prepare
  
  # 指定自定义作业文件
  %(prog)s --job_yaml /path/to/my-job.yaml
  
  # 使用额外参数
  %(prog)s --extra kernel=linux-5.10 --extra memory=8G --extra cpu=4
  
  # 输出 job_id 到文件
  %(prog)s | tee job_id.txt
        """
    )
    
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
    parser.add_argument('--extra', action='append', default=[], help='额外的键值对参数，格式为 key=value，可重复使用')
    parser.add_argument('--skip_prepare', action='store_true', help='跳过 LKP 客户端准备')
    
    args = parser.parse_args()
    
    try:
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
            extra_params=args.extra if args.extra else None
        )
        # 输出 job_id，便于管道捕获
        print(job_id)
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
