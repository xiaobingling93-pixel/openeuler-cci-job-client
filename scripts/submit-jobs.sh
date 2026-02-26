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

if [ -n "$PF_KEY" ];then
    krb5file="FILE:/tmp/krb5cc_tmppf"
    source kinit.sh
    echo "需要归档用例日志到文件服务器"
    sudo KRB5CCNAME="$krb5file" ssh tiger@$FILESERVER_IPv6 mkdir -p $FILESERVER_DIR/$BRANCH/$TIMESTAMP/testcase_logs/
    sudo KRB5CCNAME="$krb5file" scp -r ${testcase_logs_dir}/* tiger@[$FILESERVER_IPv6]:$FILESERVER_DIR/$BRANCH/$TIMESTAMP/testcase_logs/
else
    echo "无需归档用例日志到文件服务器"
fi
if [ -d "${testcase_logs_dir}" ];then
  sudo rm -rf "${testcase_logs_dir}"
fi