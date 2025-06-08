import os
import base64

from typing import Optional, Literal
from openai import OpenAI
from markitdown import MarkItDown, StreamInfo, UnsupportedFormatException
from dataclasses import dataclass

from jfs import FileSystemNode


@dataclass
class EmbeddedFile:
    id: str
    type: Literal["image"]
    # LLM 生成的简短文件名，要求唯一
    name: str
    # LLM 生成的文本描述
    description: str
    # 文件的原始内容
    content: bytes


@dataclass
class IOSYSParsedFile:
    path: str
    name: str
    created_at: str
    updated_at: str

    # 父目录的 path，根目录为 None
    parent_path: Optional[str]

    # 几百字的内容概括
    brief_text: str
    # 完整的文件文本
    verbose_text: str

    # 内嵌的文件，比如图片
    embedded_files: list[EmbeddedFile]


class IOSYSParser:
    client: OpenAI
    model: str

    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
        )
        self.model = os.environ.get("LLM_MODEL_NAME")

    def _chat(
        self,
        prompt: str,
        additional: dict,
    ) -> str:
        if not self.client or not self.model:
            raise Exception("LLM not initialized")

        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    additional,
                ],
            }
        ]

        response = self.client.chat.completions.create(
            model=self.model, messages=messages
        )

        description = response.choices[0].message.content
        return description

    def _generate_verbose(self, node: FileSystemNode):
        embedded_files = []  # type: list[EmbeddedFile]

        def image_converter(image):
            # A function using llm to get a image's description. It serves as an argument for Markitdown.
            with image.open() as image_bytes:
                img_data = image_bytes.read()
                content_type = image.content_type or "image/png"

            b64_data = base64.b64encode(img_data).decode()

            # Step 1. Get a detailed caption for the image.

            prompt = "Write a detailed caption for this image."
            data_uri = f"data:{content_type};base64,{b64_data}"
            additional = {"type": "image_url", "image_url": {"url": data_uri}}

            try:
                description = self._chat(prompt, additional)
            except Exception:
                description = "LLM Description failed"
            else:
                # Step 2. Get a concise title for the image.

                prompt = "The following text describes an image. Write a consise title for the image based on the text."
                additional = {"type": "text", "text": description}

                try:
                    name = self._chat(prompt, additional)
                except Exception:
                    name = "LLM Description failed"

            embedded_files.append(
                EmbeddedFile(
                    id=f"{node.path}/{len(embedded_files)}",
                    type="image",
                    name=name,
                    description=description,
                    content=img_data,
                )
            )

            return {
                "src": "data:{0};base64,{1}".format(content_type, b64_data),
                "alt": description,
            }

        md = MarkItDown(
            llm_client=self.client,
            llm_model=self.model,
            image_converter=image_converter,
        )
        
        try:
            result = md.convert_stream(
                node.read_stream(),
                stream_info=StreamInfo(
                    filename=node.name,
                ),
            )
            return (result.text_content, embedded_files)
        except UnsupportedFormatException:
            return ("ERROR: Unsupported file format", [])

    def _generate_brief(
        self, verbose: str, node: FileSystemNode
    ) -> str:  # the node argument is useless for now
        prompt = "Generate an abstracted text summarized from the following text."
        additional = {"type": "text", "text": verbose}

        try:
            description = self._chat(prompt, additional)
            return description

        except Exception as e:
            return str(e)

    def parse(self, node: FileSystemNode):
        (verbose_text, embedded_files) = self._generate_verbose(node)
        brief_text = self._generate_brief(verbose_text, node)

        return IOSYSParsedFile(
            path=node.path,
            name=node.name,
            created_at=114514,
            updated_at=1919810,
            parent_path=node.parent().path,
            verbose_text=verbose_text,
            brief_text=brief_text,
            embedded_files=embedded_files,
        )
