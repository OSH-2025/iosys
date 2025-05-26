#!/bin/bash
set -e

# 配置区
JUICE_VERSION="1.2.3"                  # JuiceFS版本
MOUNT_POINT="./fs"                     # 挂载点
BIN_DIR="./jfs/juicefs"                    # 客户端目录
CACHE_DIR="./jfs/cache"                    # 缓存目录
LOCAL_META="./jfs/jfs.db"        # 元数据文件（绝对路径）
LOCAL_STORAGE="./jfs/storage"         # 存储目录（绝对路径）
FS_NAME="myjfs"                        # 文件系统名称

# 自动清理函数
cleanup() {
    find "${BIN_DIR}" -type f ! -name 'juicefs' -delete
}

# 检查依赖
if ! which fuse-overlayfs >/dev/null; then
    echo "安装FUSE..."
    sudo apt-get install -y fuse3 || sudo yum install -y fuse3
fi

# 创建目录
mkdir -p "${BIN_DIR}" "${MOUNT_POINT}" "${CACHE_DIR}" "${LOCAL_META%/*}" "${LOCAL_STORAGE}"

# 安装到 目录下
curl -sSL https://d.juicefs.com/install | sh -s "${BIN_DIR}"

# 初始化文件系统
echo "初始化单机文件系统..."
"${BIN_DIR}/juicefs" format \
    --storage="file" \
    --bucket="${LOCAL_STORAGE}" \
    "sqlite3://${LOCAL_META}?mode=rwc" \
    "${FS_NAME}"  # 使用变量传递名称

# 挂载文件系统
echo "挂载到 ${MOUNT_POINT}..."
"${BIN_DIR}/juicefs" mount \
    --cache-dir="${CACHE_DIR}" \
    --cache-size 1024 \
    --background \
    "sqlite3://${LOCAL_META}" \
    "${MOUNT_POINT}"

cleanup
echo "挂载完成！"
echo -e "使用指南：\n卸载：fusermount -u ${MOUNT_POINT}\n状态：${BIN_DIR}/juicefs status sqlite3://${LOCAL_META}"
