#!/bin/bash
#==============Jenkin执行的shell==============
#mkdir -p /c/
#cd /c/
#REPOS=(
#        "/c/Jenkins-jobs|https://gitcode.com/cicd-sig/Jenkins-jobs.git"
#    "/c/lkp-tests|https://gitcode.com/cicd-sig/lkp-tests.git"
#)
#
#for item in "${REPOS[@]}"; do
#    DIR="${item%%|*}"
#    URL="${item##*|}"
#    echo "处理: $DIR"
#    if [ -d "$DIR" ]; then
#        echo "  git pull $DIR..."
#        cd "$DIR" && git pull && cd -
#    else
#        echo " git clone $URL to $DIR..."
#        git clone "$URL" "$DIR"
#    fi
#    echo "done: $DIR"
#    echo "---"
#done
#cd /c/Jenkins-jobs/scripts
#bash -x submit-jobs.sh

#==============Jenkin配置的变量==============
TIMESTAMP=${TIMESTAMP-"202512111800"}
sched_host=${sched_host-"10.232.168.215"}
sched_port=${sched_port-30100}
job_yaml=${job_yaml-"host-info.yaml"}
OS=${OS-"debian"}
ARCH=${ARCH-"aarch64"}
testbox=${testbox-"vm-2p8g"}

cd /c/Jenkins-jobs
sudo apt install -y python3-requests
sudo python3 setup.py
sudo python3 src/submit_wait_job.py \
--os ${OS} \
--os_arch ${ARCH} \
--os_version ${TIMESTAMP} \
--testbox ${testbox} \
--job_yaml ${job_yaml} \
--sched_host ${sched_host} \
--sched_port ${sched_port} \
--poll_interval 10 \
--timeout 86400 \
--extra os_mount=initramfs