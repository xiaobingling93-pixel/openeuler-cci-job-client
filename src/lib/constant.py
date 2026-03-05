#!/usr/bin/env python3
"""
constant.py - 配置文件常量

定义项目中使用的常量，便于统一管理和修改。
"""

from pathlib import Path

# CCI 仓库根目录，默认为 /c
CCI_REPOS = "/c"

# LKP 源代码路径，默认为 /c/lkp-tests
LKP_SRC_PATH = Path(CCI_REPOS) / "lkp-tests"

# 作业提交默认参数
OS_NAME = "openeuler"
OS_ARCH = "aarch64"
OS_VERSION = "24.03-LTS"
TESTBOX = "vm-2p8g"
MY_ACCOUNT = "my_account"
MY_NAME = "my_name"
MY_TOKEN = "my_token"
MY_EMAIL = "my_email@qq.com"
JOB_YAML = "host-info.yaml"
SCHED_PORT = 3000
SCHED_HOST = "172.168.178.181"
SRV_HTTP_PORT = 20007
# 获取结果信息请求重试参数
MAX_RETRIES = 3
RETRY_DELAY = 5