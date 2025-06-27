# JuiceFs 脚本使用

## Windows

- 下载并安装 https://winfsp.dev/rel/
- 下载 https://github.com/juicedata/juicefs/releases/download/v1.2.3/juicefs-1.2.3-windows-amd64.tar.gz
- 将其中的 `juicefs.exe` 放到 PATH 中

## Linux

在项目根目录下(iosys)运行脚本：

```bash
source jfs/scripts/juiceFsInit_linux.sh
```

## JuiceFs 分布式服务部署

> 分布式服务的client运行不需要额外其他部署，以下部署仅作验证。

### Linux、macOS

Linux、macOS 可用下方命令将客户端安装至 ./jfs/juicefs 。

```bash
curl -L https://juicefs.com/static/juicefs -o ./jfs/juicefs
sudo chmod +x ./
sudo chmod +x ./jfs/juicefs
```

在python sdk首次运行client时客户端将会交互式地询问一系列认证信息，你需要文件系统的 token，以及对象存储 API 密钥（确保对 Bucket 有完全操控权限）。

```bash
Token for myjfs: xxxxx
Access key ID for oss://juicefs-myjfs: xxxxx
Access key secret for oss://juicefs-myjfs: xxxxx
OK, myjfs is ready at /jfs.
```

### Windows

从 5.2 开始，JuiceFS 开始公测 Windows 客户端。如果不希望使用 Beta 版本，也可以通过 WSL 2 在 Linux 子系统中使用 JuiceFS 云服务客户端，安装和使用流程与 Linux 无异。但由于 WSL 2 需要硬件虚拟化，云主机往往无此条件，请提前确认。

[点此下载](https://s.juicefs.com/static/Windows/juicefs.exe) Windows 客户端，除此之外还应该安装 WinFsp 才能实现对 FUSE 的支持。

安装完毕以后，客户端的前台挂载需以管理员模式运行 CMD 或 PowerShell 程序，并打开 JuiceFS 客户端检查是否可以正常执行。

```bash
PS C:\> ./juicefs.exe -V
juicefs version 5.2.1 (2025-05-28 6ebc8e9)
```

## JuiceFs Python SDK

使用 python SDK 需要：

```bash
sudo apt install git-lfs
git lfs install --local
git lfs pull
```

### Client 类

Client 类是 JuiceFS 服务的客户端类，用于与 JuiceFS 进行交互。

#### 初始化方法

SDK 初始化的过程，完成了客户端认证（获取配置文件），以及连接元数据、建立客户端会话。过程十分类似在使用 JuiceFS 客户端的时候，需要先 auth 再 mount，因此需要传入的参数也可以参考 juicefs auth 及 juicefs mount 命令的选项说明。

需要特别注意：

因为使用场景有很大区别，SDK 的特定选项的默认值和 FUSE 客户端不同，以更好适配 SDK 的常见使用场景，例如：
cache_dir 的默认值是 memory；
cache_size 的默认值是 100M。
console_url 只有在私有部署环境下才需要修改，改成集群实际的 Web 控制台访问地址。

---

```py
open()

Client.open(path, mode='r', buffering=-1, encoding=None, errors=None, newline=None)
```

参数说明：

```py
path (str)：文件路径
mode (str)：文件打开模式
buffering (int)：缓冲区大小
encoding (str)：文件编码
errors (str)：错误处理策略
newline (str)：换行符处理策略
返回值：

返回一个 File 对象
```

```py
makedirs()

Client.makedirs(path, mode=0o777, exist_ok=False)
```

参数说明：

```py
path (str)：目录路径
mode (int)：目录权限
exist_ok (bool)：如果目录已存在，是否忽略错误
返回值：

无返回值
```

```py
exists()

Client.exists(path)
```

参数说明：

```py
path (str)：文件或目录路径
返回值：

返回一个布尔值，表示文件或目录是否存在
```

```py
remove()

Client.remove(path)
```

参数说明：

```py
path (str)：文件路径
返回值：

无返回值
```

```py
chmod()

Client.chmod(path, mode)
```

参数说明：

```py
path (str)：文件路径
mode (int)：文件权限
返回值：

无返回值
```

```py
symlink()

Client.symlink(src, dst)
```

参数说明：

```py
src (str)：源文件路径
dst (str)：目标符号链接路径
返回值：

无返回值
```

```py
readlink()

Client.readlink(path)
```

参数说明：

```py
path (str)：符号链接路径
返回值：

返回符号链接的目标路径
```

```py
unlink()

Client.unlink(path)
```

参数说明：

```py
path (str)：符号链接路径
返回值：

无返回值
```

```py
setxattr()

Client.setxattr(path, name, value, flags=0)
```

参数说明：

```py
path (str)：文件路径
name (str)：扩展属性名称
value (bytes)：扩展属性值
flags (int)：扩展属性标志
返回值：

无返回值
```

```py
getxattr()

Client.getxattr(path, name)
```

参数说明：

```py
path (str)：文件路径
name (str)：扩展属性名称
返回值：

返回扩展属性值
```

### File 类

File 类是 JuiceFS 文件操作的类，用于读写文件。

初始化方法

通常使用 Client.open() 方法来初始化 File 对象，不会直接创建。

```py
fileno()

File.fileno()

返回值：

返回文件描述符
```

```py
isatty()

File.isatty()

返回值：

返回一个布尔值，表示文件是否为 TTY
```

```py
read()

File.read(size=-1)

参数说明：

size (int)：读取的字节数，默认为 -1，表示读取整个文件
返回值：

返回读取的字节数据
```

```py
write()

File.write(data)

参数说明：

data (bytes)：要写入的数据
返回值：

返回写入的字节数
```

```py
close()

File.close()

返回值：

无返回值
```

```py
flush()

File.flush()

返回值：

无返回值
```

```py
readlines()

File.readlines(hint=-1)

参数说明：

hint (int)：读取的行数，默认为 -1，表示读取所有行
返回值：

返回一个包含文件行的列表
```

```py
writelines()

File.writelines(lines)

参数说明：

lines (list)：要写入的行列表
返回值：

无返回值
```

```py
seek()

File.seek(offset, whence=0)

参数说明：

offset (int)：偏移量
whence (int)：偏移基准，0 表示从文件开头，1 表示从当前位置，2 表示从文件末尾
返回值：

返回新的文件指针位置
```

```py
tell()

File.tell()

返回值：

返回当前文件指针位置
```

```py
truncate()

File.truncate(size=None)

参数说明：

size (int)：截断后的文件大小，默认为当前文件指针位置
返回值：

无返回值
```

```py
readable()

File.readable()

返回值：

返回一个布尔值，表示文件是否可读
```

```py
writable()

File.writable()

返回值：

返回一个布尔值，表示文件是否可写
```

```py
seekable()

File.seekable()

返回值：

返回一个布尔值，表示文件是否可寻址
```
