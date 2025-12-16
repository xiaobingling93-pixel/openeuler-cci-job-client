# 提交等待任务使用文档

## 项目概述

本项目提供三个 Python 脚本，用于自动化提交 LKP（Linux Kernel Performance）测试作业并等待其完成。主要功能包括：

- **submit_job.py**：提交 LKP 作业到调度器，返回作业 ID（job_id）
- **wait_job_finish.py**：轮询作业状态，直到作业完成或超时
- **submit_wait_job.py**：组合上述两个脚本的功能，一次性提交作业并等待其完成

这些脚本可以单独使用，也可以组合使用以实现完整的作业提交与监控流程。

## 环境要求

### 操作系统
- Linux 发行版（推荐 OpenEuler、Debian/Ubuntu、CentOS/RHEL）
- 需要 root 或 sudo 权限安装系统依赖

### 软件依赖
- Python 3.6+
- Git
- cpio
- Ruby 和 gem
- Ruby gems: rest-client, concurrent-ruby
- LKP 客户端（脚本会自动克隆）

#### 安装python依赖
openeuler系统
```bash
pip install -r requirements.txt
```
debian系统
```bash
apt install -y python3-requests
```

## 安装与配置

### 1. 获取代码
```bash
# 克隆项目仓库（请替换为实际仓库地址）
git clone https://github.com/your-org/Jenkins-jobs.git
cd Jenkins-jobs
```

### 2. 安装系统依赖
项目提供了 `setup.py` 脚本自动安装依赖：

```bash
# 自动检测系统并安装依赖
需要在项目根目录下执行
python3 setup.py

# 如果自动检测失败，可以强制指定系统类型
python3 setup.py --force-debian    # Debian/Ubuntu 系统
python3 setup.py --force-openeuler # OpenEuler/CentOS/RHEL 系统

# 跳过 Python 依赖安装（如果已安装）
python3 setup.py --skip-python
```

### 3. 验证安装
安装完成后，可以运行以下命令验证脚本是否可用：

```bash
# 查看脚本帮助信息
python3 src/submit_job.py --help
python3 src/wait_job_finish.py --help
python3 src/submit_wait_job.py --help

# 检查 Python 依赖
python3 -c "import requests; import json; print('依赖检查通过')"
```

### 4. 配置调度器信息
默认调度器地址为 `172.168.178.181:3000`，如需修改可在命令行参数中指定。

## 使用说明

### 提交作业 (submit_job.py)

#### 基本用法
```bash
python3 src/submit_job.py
```
使用默认参数提交作业，返回 job_id。

#### 常用参数
```bash
python3 src/submit_job.py \
  --os openeuler \
  --os_arch aarch64 \
  --os_version 24.03-LTS \
  --testbox vm-2p8g \
  --my_account your_account \
  --my_name your_name \
  --my_token your_token \
  --my_email your_email@example.com \
  --job_yaml host-info.yaml \
  --sched_host 192.168.1.100 \
  --sched_port 3000
```

#### 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--os` | `openeuler` | 操作系统名称 |
| `--os_arch` | `aarch64` | 操作系统架构 |
| `--os_version` | `24.03-LTS` | 操作系统版本 |
| `--testbox` | `vm-2p8g` | 测试机类型 |
| `--my_account` | `my_account` | 用户账户 |
| `--my_name` | `my_name` | 用户姓名 |
| `--my_token` | `my_token` | 认证令牌 |
| `--my_email` | `my_email@qq.com` | 用户邮箱 |
| `--job_yaml` | `host-info.yaml` | 作业 YAML 文件路径 |
| `--sched_host` | `172.168.178.181` | 调度器主机地址 |
| `--sched_port` | `3000` | 调度器端口 |
| `--extra` | 无 | 额外的键值对参数，格式为 key=value，可重复使用 |
| `--skip_prepare` | 无 | 跳过 LKP 客户端准备（如果已存在） |

#### 输出示例
```
============================================================
步骤2: 准备 LKP 客户端环境
============================================================
LKP_SRC 路径为 /c/lkp-tests
============================================================
步骤3: 提交作业 host-info.yaml
============================================================
执行命令: /c/lkp-tests/sbin/submit host-info.yaml
提交后返回的信息: got job id=123456, ...
提交任务成功，job id = 123456
123456
```

最后一行输出的 `123456` 就是 job_id，可用于后续监控。

### 等待作业完成 (wait_job_finish.py)

#### 基本用法
```bash
python3 src/wait_job_finish.py --job_id 123456
```

#### 常用参数
```bash
python3 src/wait_job_finish.py \
  --job_id 123456 \
  --sched_host 192.168.1.100 \
  --sched_port 3000 \
  --poll_interval 5 \
  --timeout 7200
```

#### 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--job_id` | 必填 | 作业 ID（从 submit_job.py 获取） |
| `--sched_host` | `172.168.178.181` | 调度器主机地址 |
| `--sched_port` | `3000` | 调度器端口 |
| `--poll_interval` | `10` | 轮询间隔（秒） |
| `--timeout` | `86400` | 最长等待时间（秒），默认24小时 |

#### 状态说明
脚本会轮询作业状态，直到作业进入以下终止状态：
- `finish`：作业正常完成
- `abort_invalid`：作业因无效而中止
- `abort_provider`：作业因提供者问题而中止

#### 输出示例
```
============================================================
步骤1: 轮询任务状态，API: http://172.168.178.181:3000/scheduler/v1/jobs/123456?fields=job_stage
============================================================
当前任务状态：running
当前任务状态：running
当前任务状态：finish
任务已终止，状态：finish
任务最终状态：finish
任务完整信息：{...}
```

### 提交并等待作业完成 (submit_wait_job.py)

#### 基本用法
```bash
python3 src/submit_wait_job.py
```
使用默认参数提交作业并等待其完成。

#### 常用参数
```bash
python3 src/submit_wait_job.py \
  --os openeuler \
  --os_arch aarch64 \
  --os_version 24.03-LTS \
  --testbox vm-2p8g \
  --my_account your_account \
  --my_name your_name \
  --my_token your_token \
  --my_email your_email@example.com \
  --job_yaml host-info.yaml \
  --sched_host 192.168.1.100 \
  --sched_port 3000 \
  --poll_interval 10 \
  --timeout 86400
```

#### 参数说明
| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--os` | `openeuler` | 操作系统名称 |
| `--os_arch` | `aarch64` | 操作系统架构 |
| `--os_version` | `24.03-LTS` | 操作系统版本 |
| `--testbox` | `vm-2p8g` | 测试机类型 |
| `--my_account` | `my_account` | 用户账户 |
| `--my_name` | `my_name` | 用户姓名 |
| `--my_token` | `my_token` | 认证令牌 |
| `--my_email` | `my_email@qq.com` | 用户邮箱 |
| `--job_yaml` | `host-info.yaml` | 作业 YAML 文件路径 |
| `--sched_host` | `172.168.178.181` | 调度器主机地址 |
| `--sched_port` | `3000` | 调度器端口 |
| `--extra` | 无 | 额外的键值对参数，格式为 key=value，可重复使用 |
| `--skip_prepare` | 无 | 跳过 LKP 客户端准备（如果已存在） |
| `--poll_interval` | `10` | 轮询间隔（秒） |
| `--timeout` | `86400` | 最长等待时间（秒），默认24小时 |

#### 输出示例
```
============================================================
步骤1: 提交 LKP 作业
============================================================
...（submit_job.py 的输出）...
作业提交成功，job_id = 123456
============================================================
步骤2: 等待作业 123456 完成
============================================================
...（wait_job_finish.py 的输出）...
任务最终状态：finish
============================================================
完成: 作业处理完毕
============================================================
```

#### 注意事项
- 该脚本依次调用 `submit_job.py` 和 `wait_job_finish.py`，因此需要确保这两个脚本的依赖已满足。
- 如果提交失败，脚本会立即退出，不会进入等待阶段。
- 如果等待超时，脚本会以非零状态码退出。

### 组合使用示例

#### 示例1：提交并等待完成（简单管道）
```bash
# 提交作业并获取 job_id
JOB_ID=$(python3 src/submit_job.py --my_account real_account --my_token real_token)

# 等待作业完成
python3 src/wait_job_finish.py --job_id $JOB_ID
```

#### 示例2：提交并等待完成（完整脚本）
```bash
#!/bin/bash

# 提交作业
echo "正在提交作业..."
JOB_ID=$(python3 src/submit_job.py \
  --os openeuler \
  --os_arch aarch64 \
  --testbox vm-4p16g \
  --my_account "test_user" \
  --my_token "xxxxxx" \
  --job_yaml "my-test.yaml")

echo "作业 ID: $JOB_ID"

# 等待作业完成
echo "等待作业完成..."
python3 src/wait_job_finish.py \
  --job_id $JOB_ID \
  --poll_interval 5 \
  --timeout 3600

if [ $? -eq 0 ]; then
  echo "作业已完成"
else
  echo "作业等待失败"
  exit 1
fi
```

#### 示例3：批量提交多个作业
```bash
#!/bin/bash

for i in {1..5}; do
  echo "提交第 $i 个作业..."
  JOB_ID=$(python3 src/submit_job.py --job_yaml "job$i.yaml")
  echo "作业 $i ID: $JOB_ID"
  # 可以并行等待或记录 ID 后续处理
done
```

## 配置文件管理

项目提供了一个集中化的配置文件 `src/lib/constant.py`，用于管理所有脚本的默认参数。通过修改该文件，可以统一调整默认值，而无需修改多个脚本。

### 配置文件结构

```python
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
```

### 如何使用

1. **修改默认值**：直接编辑 `src/lib/constant.py` 中对应的常量值，保存即可。
2. **脚本自动使用**：`submit_job.py` 和 `submit_wait_job.py` 会自动导入这些常量作为命令行参数的默认值。
3. **优先级**：命令行参数仍然优先于配置文件中的默认值。即如果通过 `--os` 指定了操作系统，则使用命令行参数，否则使用配置文件中的 `OS_NAME`。

### 示例

假设需要将默认调度器主机改为 `192.168.1.100`，只需修改 `SCHED_HOST` 常量：

```python
SCHED_HOST = "192.168.1.100"
```

之后运行脚本时，如果不指定 `--sched_host`，将自动使用新的默认值。

### 注意事项

- 修改配置文件后，无需重启任何服务，下次运行脚本时立即生效。
- 确保常量值的类型与脚本期望的类型一致（例如 `SCHED_PORT` 为整数）。
- 如果常量值包含路径，请使用正确的路径分隔符（Linux 使用 `/`）。

## 高级配置

### 自定义 LKP 客户端路径
默认情况下，脚本会在 `/c/lkp-tests` 目录克隆 LKP 客户端。如需使用已有的 LKP 客户端，可以使用 `--skip_prepare` 参数跳过克隆步骤，并确保 `LKP_SRC` 环境变量指向正确的路径。

### 自定义作业 YAML 文件
LKP 作业使用 YAML 文件定义测试内容。你可以创建自己的 YAML 文件：

```yaml
# my-test.yaml
suite: hackbench
testbox: vm-2p8g
os: openeuler
os_arch: aarch64
os_version: 24.03-LTS
```

然后在提交时指定：
```bash
python3 src/submit_job.py --job_yaml my-test.yaml
```

### 环境变量配置
除了命令行参数，也可以通过环境变量设置默认值：

```bash
export SCHED_HOST="192.168.1.100"
export SCHED_PORT="3000"
export MY_ACCOUNT="my_account"
export MY_TOKEN="my_token"

# 脚本会自动使用这些环境变量
python3 src/submit_job.py
```

## 故障排除

### 常见问题

#### 1. 提交失败：未找到 LKP 客户端
**错误信息**：`提交命令不存在: /c/lkp-tests/sbin/submit`
**解决方案**：
- 确保有 `/c` 目录的写入权限
- 或者使用 `--skip_prepare` 并手动设置 LKP_SRC 环境变量
- 手动克隆 LKP 客户端：`git clone https://gitee.com/compass-ci/lkp-tests.git /c/lkp-tests`

#### 2. 认证失败
**错误信息**：`提交失败: authentication failed`
**解决方案**：
- 检查 `--my_token` 参数是否正确
- 确保账户有提交作业的权限
- 联系调度器管理员验证账户信息

#### 3. 网络连接问题
**错误信息**：`请求异常：Connection refused`
**解决方案**：
- 检查调度器地址和端口是否正确
- 确认网络连通性：`ping <sched_host>`
- 确认调度器服务是否运行

#### 4. 作业长时间不完成
**解决方案**：
- 使用 `--timeout` 参数设置合理的超时时间
- 检查调度器日志了解作业状态
- 考虑手动中止作业

### 调试模式
如需查看详细调试信息，可以修改脚本或添加日志：

```python
# 临时修改：在 submit_job.py 中添加
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 脚本内部工作原理

### submit_job.py 流程
1. 准备 LKP 客户端环境（克隆仓库）
2. 设置环境变量（操作系统、架构、测试机等）
3. 执行 `lkp-tests/sbin/submit` 命令提交 YAML 作业
4. 从输出中提取 job_id
5. 返回 job_id

### wait_job_finish.py 流程
1. 构造调度器 API URL：`http://<host>:<port>/scheduler/v1/jobs/<job_id>?fields=job_stage`
2. 定期轮询作业状态
3. 判断状态是否为终止状态（finish/abort*）
4. 输出最终状态和完整信息

### submit_wait_job.py 流程
1. 调用 `submit_job.py` 的提交功能，获取作业 ID
2. 调用 `wait_job_finish.py` 的轮询功能，等待作业完成
3. 整合两个步骤的输出和错误处理，提供统一的执行流程

## 脚本返回码

三个脚本都遵循以下返回码约定：

- **0**：成功完成
- **1**：参数错误或用户输入错误
- **2**：网络连接失败或调度器不可用
- **3**：作业提交失败（认证、权限等问题）
- **4**：作业等待超时
- **5**：系统依赖缺失（LKP 客户端等）
- **其他非零值**：未预期的异常

在 Shell 脚本中可以通过 `$?` 检查返回码：

```bash
python3 src/submit_job.py
if [ $? -eq 0 ]; then
    echo "提交成功"
else
    echo "提交失败，返回码: $?"
fi
```
