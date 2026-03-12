#!/bin/bash

#==============Jenkin配置的变量==============
TIMESTAMP=${TIMESTAMP-"202512111800"}
sched_host=${sched_host-"10.232.168.215"}
sched_port=${sched_port-30100}
job_yaml=${job_yaml-"host-info.yaml"}
OS=${OS-"debian"}
ARCH=${ARCH-"aarch64"}
testbox=${testbox-"vm-2p8g"}
timeout=${timeout-86400}
tbox_spec=${tbox_spec-""}
tbox_api_key=${tbox_api_key-""}
tbox_api_url=${tbox_api_url-""}
poll_interval=${poll_interval-10}
extra=${extra-"os_mount=initramfs"}

testcase_dir="${WORKSPACE}/testcase_logs"
if [ ! -d "${testcase_dir}" ];then
  sudo mkdir -p ${testcase_dir}
fi
echo "当前执行用户：$(whoami)"
echo "the testcase is ${job_yaml}, and the logs dir is ${testcase_logs_dir}"
# 获取脚本所在目录的绝对路径
script_cur_dir=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
# 获取脚本所在目录的上一层目录
parent_dir=$(dirname "$script_cur_dir")
cd ${parent_dir}
sudo apt install -y python3-requests
sudo python3 setup.py
python3 -u src/submit_wait_job.py \
--os ${OS} \
--os_arch ${ARCH} \
--os_version ${TIMESTAMP} \
--testbox ${testbox} \
--job_yaml ${job_yaml} \
--sched_host ${sched_host} \
--sched_port ${sched_port} \
--poll_interval ${poll_interval} \
--timeout ${timeout} \
--tbox_spec "${tbox_spec}" \
--tbox_api_key "${tbox_api_key}" \
--tbox_api_url "${tbox_api_url}" \
--extra "${extra}" \
--logs_dir ${testcase_dir}
