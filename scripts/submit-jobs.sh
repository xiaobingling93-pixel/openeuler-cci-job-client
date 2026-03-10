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
poll_interval=${poll_interval-10}
extra=${extra-"os_mount=initramfs"}

testcase_dir="tmp/testcase_logs"
if [ ! -d "${testcase_dir}" ];then
  sudo mkdir -p ${testcase_dir}
fi
testcase_logs_dir=$(sudo mktemp -d -p "${testcase_dir}" "XXXXXX")
echo "当前执行用户：$(whoami)"
echo "the testcase is ${job_yaml}, and the logs dir is ${testcase_logs_dir}"
cd /c/Jenkins-jobs
sudo apt install -y python3-requests
sudo python3 setup.py
sudo python3 -u src/submit_wait_job.py \
--os ${OS} \
--os_arch ${ARCH} \
--os_version ${TIMESTAMP} \
--testbox ${testbox} \
--job_yaml ${job_yaml} \
--sched_host ${sched_host} \
--sched_port ${sched_port} \
--poll_interval ${poll_interval} \
--timeout ${timeout} \
--extra "${extra}" \
--logs_dir ${testcase_logs_dir}

#放到workspace下面，方便归档到文件服务器
if [ -n "$(ls -A "${testcase_logs_dir}")" ];then
  mkdir -p "${WORKSPACE}"/testcase_logs/
  cp -a "${testcase_logs_dir}"/. "${WORKSPACE}"/testcase_logs/
fi

if [ -d "${testcase_logs_dir}" ];then
  sudo rm -rf "${testcase_logs_dir}"
fi