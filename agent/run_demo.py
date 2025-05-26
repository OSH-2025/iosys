#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import argparse
import json
from dotenv import load_dotenv

from src.app import FileManagerApp
from src.config import AgentConfig


def setup_args_parser() -> argparse.ArgumentParser:
    """设置命令行参数解析器"""
    parser = argparse.ArgumentParser(description='基于LLM的文件管理Agent')

    parser.add_argument('--base-dir', type=str, default='./data',
                        help='基础目录，所有文件操作将在此目录下执行 (默认: ./data)')

    parser.add_argument('--command', type=str,
                        help='要执行的单条命令')

    parser.add_argument('--demo', action='store_true',
                        help='运行演示模式 (默认)')

    return parser


def process_single_command(app: FileManagerApp, command: str) -> dict:
    """处理单条命令"""
    result = app.process_command(command)
    return result


def run_demo(app: FileManagerApp) -> None:
    """运行演示程序"""
    # 示例命令
    commands = [
        "创建一个名为notes.txt的文件",
        "创建一个名为documents的文件夹",
        "在documents目录下创建一个名为report.md的文件",
        "将'# 演示报告\n\n这是一个演示报告'写入documents/report.md文件"
    ]

    # 确保数据目录存在
    os.makedirs("./data", exist_ok=True)

    # 执行命令
    print("=== 文件管理Agent演示 ===\n")
    for cmd in commands:
        print(f"命令: \"{cmd}\"")
        result = app.process_command(cmd)
        print(f"结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
        print("-" * 50)

    print("\n演示完成，请检查 './data' 目录查看结果")


def main():
    """主函数"""
    parser = setup_args_parser()
    args = parser.parse_args()

    # 确保基础目录存在
    base_dir = args.base_dir or os.environ.get('BASE_DIR', './data')
    os.makedirs(base_dir, exist_ok=True)
    # 创建配置，确保base_dir是绝对路径
    abs_base_dir = os.path.abspath(base_dir)

    config = AgentConfig(base_dir=abs_base_dir)

    # 创建应用
    app = FileManagerApp(config)

    # 根据命令行参数决定执行模式
    if args.command:
        # 单条命令模式
        result = process_single_command(app, args.command)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        # 默认使用演示模式
        run_demo(app)


if __name__ == "__main__":
    load_dotenv()
    main()
