#!/usr/bin/env python3
# -*- encoding=utf-8 -*-
"""
# **********************************************************************************
# Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
# [cci-job-client] is licensed under the Mulan PSL v2.
# You can use this software according to the terms and conditions of the Mulan PSL v2.
# You may obtain a copy of Mulan PSL v2 at:
#          http://license.coscl.org.cn/MulanPSL2
# THIS SOFTWARE IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
# Author:
# Create: 2026-03-06
# Description: 定义项目中使用的常量，便于统一管理和修改。
# **********************************************************************************
"""
import os
from pathlib import Path

# CCI 仓库根目录
WORKSPACE = os.environ.get("WORKSPACE")
if WORKSPACE:
    CCI_REPOS = os.path.join(WORKSPACE, "c")
else:
    CCI_REPOS = "/c"

# LKP 源代码路径
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