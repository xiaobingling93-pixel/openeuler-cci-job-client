# 使用指导
该脚本用户提交用户的测试用例的job，配置到jenkins的Configure -> Buid Steps -> Execute shell -> Command

os debian 提交的job运行的系统
os_arch aarch64 提交的job运行的系统的架构
os_version 1766059721 提交的job运行的系统的版本，一般来自于制作rootfs时生成的版本
sched_host 172.168.177.42 提交的job的compass-ci服务器的调度器对外的ip地址
sched_port 30100 提交的job的compass-ci服务器的调度器对外的port
poll_interval 10 轮询查看job的状态的时间，单位是秒
timeout 86400 job运行的超时时间
extra os_mount=initramfs 指定使用rootfs启动job


```
#!/bin/bash
mkdir -p /c/
cd /c/
REPOS=(
	"/c/Jenkins-jobs|https://gitcode.com/Jenkins-jobs.git"
    "/c/lkp-tests|https://gitcode.com/lkp-tests.git"
)

for item in "${REPOS[@]}"; do
    DIR="${item%%|*}" 
    URL="${item##*|}" 
    echo "处理: $DIR"
    if [ -d "$DIR" ]; then
        echo "  git pull $DIR..."
        cd "$DIR" && git pull && cd -
    else
        echo " git clone $URL to $DIR..."
        git clone "$URL" "$DIR"
    fi
    echo "done: $DIR"
    echo "---"
done


cd /c/Jenkins-jobs
sudo apt install -y python3-requests
sudo python3 setup.py
sudo python3 src/submit_wait_job.py \
--os debian \
--os_arch aarch64 \
--os_version 1766059721 \
--testbox vm-2p8g \
--job_yaml host-info.yaml \
--sched_host 172.168.177.42 \
--sched_port 30100 \
--poll_interval 10 \
--timeout 86400 \
--extra os_mount=initramfs

```
