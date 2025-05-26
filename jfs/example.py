from juicefs import Client

# 创建 JuiceFS 客户端
jfs = Client(name="", meta="sqlite3://./jfs/jfs.db")

# 列出目录中的文件
jfs.listdir("/")
