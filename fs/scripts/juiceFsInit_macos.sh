#挂载需要macFUSE支持
#!/bin/bash
set -e

# 配置区
JUICE_VERSION="1.2.3"                  # JuiceFS版本
MOUNT_POINT="./fs"                     # 挂载点
BIN_DIR="./jfs/juicefs"                    # 客户端目录
LOCAL_META="./data/jfs.db"        # 元数据文件（绝对路径）
LOCAL_STORAGE="./jfs/storage"         # 存储目录（绝对路径）
JFS_NAME="iosys"                        # 文件系统名称

JFS_CACHE_DIR=./data/jfs_cache
JFS_LOG_FILE=./data/jfs.log
JFS_PID_FILE=./data/jfs.pid
JFS_META_URL=sqlite3://./data/jfs.db

# 自动清理函数
cleanup() {
    find "${BIN_DIR}" -type f ! -name 'juicefs' -delete
}

# 创建目录
mkdir -p "${BIN_DIR}" "${MOUNT_POINT}" "${JFS_CACHE_DIR}" "${LOCAL_META%/*}" "${LOCAL_STORAGE}"

# 安装到 目录下
curl -sSL https://d.juicefs.com/install | sh -s "${BIN_DIR}"

# 初始化文件系统
echo "初始化单机文件系统..."
"${BIN_DIR}/juicefs" format \
    --storage="file" \
    --bucket="${LOCAL_STORAGE}" \
    "${JFS_META_URL}?mode=rwc" \
    "${JFS_NAME}"  # 使用变量传递名称

# 挂载文件系统
echo "挂载到 ${MOUNT_POINT}..."
"${BIN_DIR}/juicefs" mount \
    --cache-dir="${JFS_CACHE_DIR}" \
    --cache-size 1024 \
    --background \
    "${JFS_META_URL}" \
    "${MOUNT_POINT}"

cleanup
echo "挂载完成！"
echo -e "使用指南：\n卸载：fusermount -u ${MOUNT_POINT}\n状态：${BIN_DIR}/juicefs status sqlite3://${LOCAL_META}"