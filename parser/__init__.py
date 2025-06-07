import os
import base64

from typing import Literal
from openai import OpenAI
from ..markitdown import Markitdown
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
    client: OpenAI
    model: str

    def __init__(self):
        self.client = OpenAI(
            base_url=os.environ.get("LLM_BASE_URL"),
            api_key=os.environ.get("LLM_API_KEY"),
        )
        self.model = (os.environ.get("LLM_MODEL_NAME"),)

    def _generate_basic(
        self,
        file_name: str,  # let the argument be file name, for now
    ):
        pass  # to be done

    def _generate_abtract(self, file_name: str, verbose: str):
        pass  # to be done

    def _generate_verbose(
        self,
        file_name: str,
    ):
        """isn't this part a bit too long???"""

        def image_converter(image):
            with image.open() as image_bytes:
                img_data = image_bytes.read()
                content_type = image.content_type or "image/png"

            b64_data = base64.b64encode(img_data).decode()
            prompt = "Write a detailed caption for this image."

            if not self.client or not self.model:
                return {
                    "src": "data:{0};base64,{1}".format(content_type, b64_data),
                    "alt": "image",
                }

            try:
                data_uri = f"data:{content_type};base64,{b64_data}"

                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}},
                        ],
                    }
                ]

                response = self.client.chat.completions.create(
                    model=self.model, messages=messages
                )
                description = response.choices[0].message.content

                return {
                    "src": "data:{0};base64,{1}".format(image.content_type, b64_data),
                    "alt": description,
                }

            except Exception:
                return {
                    "src": "data:{0};base64,{1}".format(image.content_type, b64_data),
                    "alt": "LLM Description failed",
                }

        md = MarkItDown(
            llm_client=self.client,
            llm_model=self.model,
            image_converter=image_converter,
        )
        result = md.convert(file_name)
        return result.text_content

    def parse(self, node: FileNode, content: str):
        pass  # to be done
