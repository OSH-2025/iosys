import asyncio
import os
import base64
from concurrent.futures import ThreadPoolExecutor

from typing import Literal
from openai import AsyncOpenAI
from markitdown import MarkItDown, StreamInfo, UnsupportedFormatException
from dataclasses import dataclass

from fs import FileSystemNode
from utils.logger import IOSYSLogger

logger = IOSYSLogger("Parser")


@dataclass
class EmbeddedFile:
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
    created_at: int
    updated_at: int

    # 父目录的 path
    parent_path: str

    # 几百字的内容概括
    brief_text: str
    # 完整的文件文本
    verbose_text: str

    # 内嵌的文件，比如图片
    embedded_files: list[EmbeddedFile]


class IOSYSParser:
    llm: AsyncOpenAI
    model: str
    md: MarkItDown

    def __init__(self, llm: AsyncOpenAI):
        self.llm = llm
        self.model = os.environ["LLM_MODEL_NAME"]
        self.md = MarkItDown(
            llm_client=self.llm,
            llm_model=self.model,
        )

    async def _chat(
        self,
        prompt: str,
        additional,
    ) -> str:
        if not self.llm or not self.model:
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

        response = await self.llm.chat.completions.create(
            model=self.model,
            messages=messages,  # type: ignore
        )

        description = response.choices[0].message.content
        assert description is not None
        return description

    def _get_extension(self, fullname: str):
        basename = os.path.basename(fullname)
        extention = os.path.splitext(basename)[1]
        # if extention == "":
        #     return ".txt"  # To make sure it can be parsed as a plain text
        return extention

    async def _generate_verbose(self, node: FileSystemNode):
        embedded_files = []  # type: list[EmbeddedFile]

        async def image_converter(image):
            # A function using llm to get a image's description. It serves as an argument for Markitdown.
            with image.open() as image_bytes:
                img_data = image_bytes.read()
                content_type = image.content_type or "image/png"

            b64_data = base64.b64encode(img_data).decode()

            # Step 1. Get a detailed caption for the image.

            prompt = "Write a detailed caption for this image."
            data_uri = f"data:{content_type};base64,{b64_data}"
            additional = {"type": "image_url", "image_url": {"url": data_uri}}
            description = await self._chat(prompt, additional)

            # Step 2. Get a concise title for the image.
            prompt = "The following text describes an image. Write a concise title for the image based on the text."
            additional = {"type": "text", "text": description}
            name = await self._chat(prompt, additional)

            embedded_files.append(
                EmbeddedFile(
                    type="image",
                    name=name,
                    description=description,
                    content=img_data,
                )
            )

            if "png" in content_type:
                source = "./{0}.png".format(name)
            else:
                source = "./{0}.jpg".format(name)

            return {
                "src": source,
                "alt": description,
            }

        def run_image_converter_in_thread(image):
            # Create a new event loop in a separate thread
            def run_async():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    return loop.run_until_complete(image_converter(image))
                finally:
                    loop.close()

            with ThreadPoolExecutor() as executor:
                future = executor.submit(run_async)
                return future.result()

        try:
            result = self.md.convert_stream(
                node.read_stream(),
                stream_info=StreamInfo(
                    filename=node.name,
                    extension=self._get_extension(node.name),
                ),
                image_converter=run_image_converter_in_thread,
            )
            return (result.markdown, embedded_files)
        except UnsupportedFormatException:
            return ("ERROR: Unsupported file format", [])

    async def _generate_brief(
        self, verbose: str, node: FileSystemNode
    ) -> str:  # the node argument is useless for now
        prompt = "Generate an abstracted text summarized from the following text."
        additional = {"type": "text", "text": verbose}

        try:
            description = await self._chat(prompt, additional)
            return description

        except Exception as e:
            return str(e)

    async def parse(self, node: FileSystemNode):
        logger.info(f"Parsing file {node.path}...")

        (verbose_text, embedded_files) = await self._generate_verbose(node)
        brief_text = await self._generate_brief(verbose_text, node)

        node.update_meta(
            verbose_text=verbose_text,
            brief_text=brief_text,
        )
        for embedded_file in embedded_files:
            embedded_node = node.create_child(embedded_file.name)
            embedded_node.write(content=embedded_file.content)
            embedded_node.update_meta(
                type=embedded_file.type,
                description=embedded_file.description,
            )

        parent = node.parent()
        if not parent:
            raise ValueError("Node must have a parent")

        logger.info(f"Parsed file {node.path} successfully.")

        return IOSYSParsedFile(
            path=node.path,
            name=node.name,
            created_at=int(node.get_meta("created_at", 0)),
            updated_at=int(node.get_meta("modified_at", 0)),
            parent_path=parent.path,
            verbose_text=verbose_text,
            brief_text=brief_text,
            embedded_files=embedded_files,
        )

    async def get_verbose_text(self, node: FileSystemNode) -> str:
        result = node.get_meta("verbose_text")
        if result is None:
            result = (await self.parse(node)).verbose_text
        return str(result)
