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
# Description: 解析参数的实用工具函数
# **********************************************************************************
"""

from typing import Optional, List

def parse_extra_params(extra_args):
    """
    解析 --extra 参数列表，仅支持空格分隔的多个键值对。
    
    Args:
        extra_args: 字符串列表，每个字符串可能包含一个或多个 key=value 对（空格分隔）
        
    Returns:
        展平后的 key=value 字符串列表
    """
    if not extra_args:
        return None
    
    result = []
    for arg in extra_args:
        # 按空格分割，忽略逗号分隔
        parts = [p.strip() for p in arg.split() if p.strip()]
        
        for part in parts:
            if '=' in part:
                result.append(part)
            else:
                # 如果分割后部分不包含等号，可能是前一个值的一部分（如值中有空格）
                # 将其与前一个合并（如果存在）
                if result and '=' in result[-1]:
                    last = result.pop()
                    key, value = last.split('=', 1)
                    # 分隔符为空格
                    result.append(f"{key}={value} {part}")
                else:
                    # 无法处理，忽略
                    continue
    return result if result else None