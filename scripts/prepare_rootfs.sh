#!/bin/bash

FILE_SERVER=${FILE_SERVER-"http://os-cicd.byted.org/fileserver"}
TARGET_IP=${TARGET_IP}
BRANCH=${BRANCH}
TIMESTAMP=${TIMESTAMP}
LOCAL_ROOTFS_DIR=${WORKSPACE}/tmp/rootfs
ARCH=${ARCH-"aarch64"}
if [ "${ARCH}" == "arm64" ];then
    ARCH="aarch64"
elif [ "${ARCH}" == "amd64" ];then
    ARCH="x86_64"
fi

# 错误处理函数
error_exit() {
    echo "error：$1" >&2
    exit 1
}

# 检查SSH免密登录
check_ssh_auth() {
    echo "check no password SSH to ${TARGET_IP}..."
    if ! ssh -o BatchMode=yes -o ConnectTimeout=5 root@${TARGET_IP} "echo ok" >/dev/null 2>&1; then
        error_exit "fail to SSH ${TARGET_IP} without password，please config it first！"
    fi
}

if [ -z ${TARGET_IP} ];then
  error_exit "compass ci scheduler ip is not given"
fi

if [ -z ${BRANCH} ];then
  error_exit "BRANCH is not given"
fi

if [ -z ${TIMESTAMP} ];then
  error_exit "TIMESTAMP is not given"
fi

# 远程服务器OS文件基础目录
OS_BASE_DIR="/srv/os/debian/${ARCH}"
# 远程服务器initrd文件基础目录
INITRD_BASE_DIR="/srv/initrd/osimage/debian/${ARCH}"
# rootfs所在的文件服务器地址
REMOTE_ROOTFS_DIR="${FILE_SERVER}/${BRANCH}/${TIMESTAMP}/rootfs"

echo "wget rootfs from ${rootfs_remote_dir}"
if [ ! -d ${LOCAL_ROOTFS_DIR} ];then
  mkdir -p ${LOCAL_ROOTFS_DIR} || error_exit "mkdir ${LOCAL_ROOTFS_DIR} failed"
fi

debina_arch=${ARCH}
if [ "${ARCH}" == "aarch64" ];then
    debina_arch="arm64"
elif [ "${ARCH}" == "x86_64" ];then
    debina_arch="amd64"
fi

wget -P ${LOCAL_ROOTFS_DIR} ${REMOTE_ROOTFS_DIR}/${debina_arch}/modules.cgz >/dev/null 2>&1 || error_exit "wget modules failed"
wget -P ${LOCAL_ROOTFS_DIR} ${REMOTE_ROOTFS_DIR}/${debina_arch}/rootfs.cgz >/dev/null 2>&1 || error_exit "wget rootfs failed"
wget -P ${LOCAL_ROOTFS_DIR} ${REMOTE_ROOTFS_DIR}/${debina_arch}/vmlinuz >/dev/null 2>&1 || error_exit "wget vmliuz failed"


echo "check the SSH connection of compass-ci"
check_ssh_auth

echo "store rootfs to compass-ci"
# 创建远程目录
ssh root@${TARGET_IP} "mkdir -p ${OS_BASE_DIR}/${TIMESTAMP}/boot/ ${INITRD_BASE_DIR}/${TIMESTAMP}/" || error_exit "mkdir remote dir failed"

# 同步内核文件并创建软链接
rsync -avz "${LOCAL_ROOTFS_DIR}/vmlinuz-${TIMESTAMP}" root@${TARGET_IP}:${OS_BASE_DIR}/${TIMESTAMP}/boot/ || error_exit "rsync vmlinuz failed"
ssh root@${TARGET_IP} "ln -sf ${OS_BASE_DIR}/${TIMESTAMP}/boot/vmlinuz-${TIMESTAMP} ${OS_BASE_DIR}/${TIMESTAMP}/boot/vmlinuz" || error_exit "link vmlinuz failed"

# 同步模块文件并创建软链接
rsync -avz "${LOCAL_ROOTFS_DIR}/modules-${TIMESTAMP}.cgz" root@${TARGET_IP}:${OS_BASE_DIR}/${TIMESTAMP}/boot/ || error_exit "rsync modules.cgz failed"
ssh root@${TARGET_IP} "ln -sf ${OS_BASE_DIR}/${TIMESTAMP}/boot/modules-${TIMESTAMP}.cgz ${OS_BASE_DIR}/${TIMESTAMP}/boot/modules.cgz" || error_exit "link modules.cgz failed"

# 同步rootfs文件并改名
rsync -avz "${LOCAL_ROOTFS_DIR}/rootfs.cgz" root@${TARGET_IP}:${INITRD_BASE_DIR}/${TIMESTAMP}/ || error_exit "rsync rootfs.cgz failed"
ssh root@${TARGET_IP} "mv -f ${INITRD_BASE_DIR}/${TIMESTAMP}/rootfs.cgz ${INITRD_BASE_DIR}/${TIMESTAMP}/current" || error_exit "rename rootfs.cgz failed"
# 复制ipconfig文件
ssh root@${TARGET_IP} "cp -f /srv/ipconfig/run-ipconfig.cgz ${INITRD_BASE_DIR}/${TIMESTAMP}/" || error_exit "copy run-ipconfig.cgz failed"