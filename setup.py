#!/usr/bin/env python3
"""
环境设置脚本
安装和管理依赖
根据系统类型（Debian/OpenEuler）安装相应的软件包
"""

import os
import sys
import subprocess
import platform
import argparse
from typing import List, Optional

def run_command(cmd: List[str], desc: str = "") -> bool:
    """
    运行命令并检查返回码
    """
    print(f"正在执行: {' '.join(cmd)}")
    if desc:
        print(f"  ({desc})")
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print(f"警告: {result.stderr}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"错误: 命令执行失败，返回码 {e.returncode}")
        print(f"标准错误: {e.stderr}")
        return False
    except FileNotFoundError:
        print(f"错误: 命令未找到，请确保系统已安装相应的包管理器")
        return False

def check_package_installed(package: str) -> bool:
    """
    检查系统包是否已安装（适用于 Debian/Ubuntu）
    """
    try:
        result = subprocess.run(['dpkg', '-s', package],
                              capture_output=True, text=True, check=False)
        return result.returncode == 0 and 'Status: install ok installed' in result.stdout
    except FileNotFoundError:
        # dpkg 不存在，使用 apt 检查
        try:
            result = subprocess.run(['apt', 'list', '--installed', package],
                                  capture_output=True, text=True, check=False)
            return package in result.stdout
        except FileNotFoundError:
            return False

def check_gem_installed(gem: str) -> bool:
    """
    检查 Ruby gem 是否已安装
    """
    try:
        result = subprocess.run(['gem', 'list', '-i', gem],
                              capture_output=True, text=True, check=False)
        return result.returncode == 0 and 'true' in result.stdout.lower()
    except FileNotFoundError:
        return False

def detect_distribution() -> str:
    """
    检测操作系统发行版
    返回 'debian', 'openeuler', 或 'unknown'
    """
    # 方法1: 通过 /etc/os-release 文件
    os_release_path = "/etc/os-release"
    if os.path.exists(os_release_path):
        with open(os_release_path, 'r') as f:
            content = f.read().lower()
            if 'debian' in content or 'ubuntu' in content:
                return 'debian'
            if 'openeuler' in content:
                return 'openeuler'
            if 'centos' in content or 'red hat' in content or 'rhel' in content:
                # OpenEuler 使用 yum/dnf，与 CentOS/RHEL 类似
                return 'openeuler'
    
    # 方法2: 通过 platform 模块
    dist = platform.system().lower()
    if dist == 'linux':
        # 进一步检查
        try:
            import distro
            name = distro.id()
            if name in ['debian', 'ubuntu', 'linuxmint']:
                return 'debian'
            if name in ['centos', 'rhel', 'fedora', 'openeuler']:
                return 'openeuler'
        except ImportError:
            pass
    
    return 'unknown'

def install_dependency_debian() -> bool:
    """
    在 Debian/Ubuntu 系统上安装依赖
    """
    print("=== 在 Debian 系系统上安装依赖 ===")
    success = True
    
    # 安装系统包（先检查是否已安装）
    packages = ['cpio', 'git', 'ruby', 'gem', 'python3-pip', 'python3-requests']
    packages_to_install = []
    
    for pkg in packages:
        if check_package_installed(pkg):
            print(f"✓ 系统包 '{pkg}' 已安装，跳过")
        else:
            print(f"✗ 系统包 '{pkg}' 未安装，将安装")
            packages_to_install.append(pkg)
    
    if packages_to_install:
        # 更新包列表
        print("检查并更新包列表...")
        if not run_command(['apt-get', 'update'], "更新包列表"):
            success = False
        print(f"安装缺失的系统包: {', '.join(packages_to_install)}")
        if not run_command(['apt-get', 'install', '-y'] + packages_to_install, "安装系统包"):
            success = False
    else:
        print("所有系统包均已安装，跳过系统包安装")
    
    # 安装 Ruby gems（先检查是否已安装）
    gems = ['rest-client', 'concurrent-ruby']
    gems_to_install = []
    
    for gem in gems:
        if check_gem_installed(gem):
            print(f"✓ Ruby gem '{gem}' 已安装，跳过")
        else:
            print(f"✗ Ruby gem '{gem}' 未安装，将安装")
            gems_to_install.append(gem)
    
    if gems_to_install:
        for gem in gems_to_install:
            if not run_command(['gem', 'install', gem], f"安装 Ruby gem: {gem}"):
                success = False
    else:
        print("所有 Ruby gems 均已安装，跳过 gem 安装")
    
    return success

def install_dependency_openeuler() -> bool:
    """
    在 OpenEuler/CentOS/RHEL 系统上安装依赖
    """
    print("=== 在 OpenEuler 系系统上安装依赖 ===")
    success = True
    
    # 安装系统包（使用 yum 或 dnf）
    # 首先检测包管理器
    if run_command(['which', 'dnf'], "检查 dnf"):
        pm = 'dnf'
    elif run_command(['which', 'yum'], "检查 yum"):
        pm = 'yum'
    else:
        print("错误: 未找到 yum 或 dnf 包管理器")
        return False
    
    # 安装包
    packages = ['cpio', 'git', 'ruby', 'rubygems']
    if not run_command([pm, 'install', '-y'] + packages, f"使用 {pm} 安装系统包"):
        success = False
    
    # 安装 Ruby gems
    gems = ['rest-client', 'concurrent-ruby']
    for gem in gems:
        if not run_command(['gem', 'install', gem], f"安装 Ruby gem: {gem}"):
            success = False
    
    return success

def install_python_dependencies() -> bool:
    """
    安装 Python 依赖（requirements.txt）
    """
    req_file = "requirements.txt"
    if os.path.exists(req_file):
        print("=== 安装 Python 依赖 ===")
        with open(req_file, 'r') as f:
            content = f.read().strip()
            if content:
                return run_command(['pip3', 'install', '-r', req_file], "安装 requirements.txt")
            else:
                print("requirements.txt 为空，跳过 Python 依赖安装")
                return True
    else:
        print(f"未找到 {req_file}，跳过 Python 依赖安装")
        return True

def main() -> int:
    parser = argparse.ArgumentParser(description='安装系统依赖')
    parser.add_argument('--force-debian', action='store_true', help='强制使用 Debian 安装方式')
    parser.add_argument('--force-openeuler', action='store_true', help='强制使用 OpenEuler 安装方式')
    parser.add_argument('--skip-python', action='store_true', help='跳过 Python 依赖安装')
    args = parser.parse_args()
    
    # 确定发行版
    dist = detect_distribution()
    if args.force_debian:
        dist = 'debian'
    elif args.force_openeuler:
        dist = 'openeuler'
    
    print(f"检测到的系统发行版: {dist}")
    
    success = True
    if dist == 'debian':
        if not install_dependency_debian():
            success = False
    elif dist == 'openeuler':
        if not install_dependency_openeuler():
            success = False
    else:
        print("错误: 无法识别操作系统发行版，无法自动安装依赖")
        print("请手动安装以下软件包:")
        print("  - cpio")
        print("  - git")
        print("  - ruby 和 gem")
        print("  - Ruby gems: rest-client, concurrent-ruby")
        success = False
    
    # 安装 Python 依赖
    #if success and not args.skip_python:
    #    if not install_python_dependencies():
    #        success = False
    
    if success:
        print("=== 所有依赖安装完成 ===")
        return 0
    else:
        print("=== 依赖安装过程中出现错误 ===")
        return 1

if __name__ == '__main__':
    sys.exit(main())