import os

from typing import Literal
from openai import OpenAI

from ..jfs import FileNode

class EmbeddedFile:
    id: str
    type: Literal["image"]
    # LLM 生成的简短文件名，要求唯一
    name: str
    # LLM 生成的文本描述
    description: str
    # 文件的原始内容
    content: bytes


class IOSYSParsedFile:
    id: str
    name: str
    created_at: str
    updated_at: str

    # 几百字的内容概括
    brief_text: str
    # 完整的文件文本
    full_text: str

    # 内嵌的文件，比如图片
    embedded_files: list[EmbeddedFile]


class IOSYSParser:
    llm: OpenAI

    def __init__(self):
        self.llm = OpenAI(
            api_base=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
            model=os.environ.get("LLM_MODEL_NAME"),
        )

    def parse(self, node: FileNode, content: str): ...
