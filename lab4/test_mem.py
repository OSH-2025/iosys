import argparse
import subprocess
import time
import psutil
import statistics
import shlex
import random
from typing import Tuple, List, Optional

# 16 个预定义的 prompt
PROMPTS = [
    "你好，Llama！",
    "请用五句话总结人工智能的发展史。",
    "写一首关于夏天的短诗。",
    "解释量子纠缠的概念。",
    "给出一道中等难度的编程面试题。",
    "如何优化 Python 代码的性能？",
    "翻译以下句子：The quick brown fox jumps over the lazy dog.",
    "模拟一次简单的对话：用户问天气，系统回答。",
    "简要介绍区块链的工作原理。",
    "列举三种常见的排序算法及其时间复杂度。",
    "为新手提供一个学习机器学习的路线图。",
    "写一个 HTTP 请求的示例代码（Python）。",
    "描述一下太阳系中各行星的顺序。",
    "如何用正则表达式匹配电子邮箱？",
    "生成一段鼓励人的话。",
    "简述深度学习和传统机器学习的区别。"
]


def measure_run(cmd: str, prompt: str, interval: float) -> Optional[Tuple[float, float]]:
    """
    启动 llama-cli，将 prompt 通过 stdin 传入；采样期间每 interval 秒记录 RSS（MB）。
    若进程退出码 != 0，返回 None 表示此次测量无效。
    返回 (avg_rss_MB, peak_rss_MB)。
    """
    parts = shlex.split(cmd)
    # 启动子进程
    proc = subprocess.Popen(parts, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    p = psutil.Process(proc.pid)

    # 发送 prompt 并关闭 stdin
    try:
        proc.stdin.write((prompt + "\n").encode())
        proc.stdin.flush()
    except Exception:
        pass
    proc.stdin.close()

    # 采样内存
    samples: List[float] = []
    while proc.poll() is None:
        try:
            rss = p.memory_info().rss / (1024 * 1024)
            samples.append(rss)
        except (psutil.NoSuchProcess, psutil.ZombieProcess):
            break
        time.sleep(interval)

    # 等待结束并获取 stderr
    proc.wait()
    err = proc.stderr.read().decode().strip()

    if proc.returncode != 0:
        print(f"  [错误] 退出码 {proc.returncode}: {err}")
        return None

    if not samples:
        return None

    return statistics.mean(samples), max(samples)


def main():
    parser = argparse.ArgumentParser(
        description="测量 llama-cli 推理内存占用的平均值和峰值，随机使用预定义的 16 个 prompt。"
    )
    parser.add_argument("-c", "--cmd", required=True,
        help="启动 llama-cli 的命令，不含 prompt 部分，例如：\n"
             "./main -m ./models/ggml-model.bin -n 128"
    )
    parser.add_argument("-n", "--runs", type=int, default=5,
        help="重复测量次数，默认为 5"
    )
    parser.add_argument("-i", "--interval", type=float, default=0.1,
        help="内存采样间隔（秒），默认为 0.1"
    )
    args = parser.parse_args()

    avgs: List[float] = []
    peaks: List[float] = []

    print(f"开始测量：{args.runs} 次，每次间隔 {args.interval}s")
    for i in range(1, args.runs + 1):
        prompt = random.choice(PROMPTS)
        print(f"运行 {i}/{args.runs}，Prompt: {prompt} …", end=" ")

        res = measure_run(args.cmd, prompt, args.interval)
        if res is None:
            print("跳过")
            continue
        avg, peak = res
        print(f"平均 {avg:.2f} MB，峰值 {peak:.2f} MB")
        avgs.append(avg)
        peaks.append(peak)

    if not avgs:
        print("未能测量到有效的运行。请检查 llama-cli 命令和参数是否正确。")
        return

    print("\n==== 总体统计 ====")
    print(f"各次平均值的平均: {statistics.mean(avgs):.2f} MB")
    print(f"各次峰值的平均: {statistics.mean(peaks):.2f} MB")
    print(f"最大峰值:       {max(peaks):.2f} MB")

if __name__ == "__main__":
    main()