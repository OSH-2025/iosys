import sys
import base64

from typing import BinaryIO, Any

from ._html_converter import HtmlConverter
from ..converter_utils.docx.pre_process import pre_process_docx
from .._base_converter import DocumentConverter, DocumentConverterResult
from .._stream_info import StreamInfo
from .._exceptions import MissingDependencyException, MISSING_DEPENDENCY_MESSAGE

# Try loading optional (but in this case, required) dependencies
# Save reporting of any exceptions for later
_dependency_exc_info = None
try:
    import mammoth
except ImportError:
    # Preserve the error and stack trace for later
    _dependency_exc_info = sys.exc_info()


ACCEPTED_MIME_TYPE_PREFIXES = [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]

ACCEPTED_FILE_EXTENSIONS = [".docx"]


class DocxConverter(HtmlConverter):
    """
    Converts DOCX files to Markdown. Style information (e.g.m headings) and tables are preserved where possible.
    """

    def __init__(self):
        super().__init__()
        self._html_converter = HtmlConverter()

    def accepts(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,  # Options to pass to the converter
    ) -> bool:
        mimetype = (stream_info.mimetype or "").lower()
        extension = (stream_info.extension or "").lower()

        if extension in ACCEPTED_FILE_EXTENSIONS:
            return True

        for prefix in ACCEPTED_MIME_TYPE_PREFIXES:
            if mimetype.startswith(prefix):
                return True

        return False

    def convert(
        self,
        file_stream: BinaryIO,
        stream_info: StreamInfo,
        **kwargs: Any,  # Options to pass to the converter
    ) -> DocumentConverterResult:
        # Check: the dependencies
        if _dependency_exc_info is not None:
            raise MissingDependencyException(
                MISSING_DEPENDENCY_MESSAGE.format(
                    converter=type(self).__name__,
                    extension=".docx",
                    feature="docx",
                )
            ) from _dependency_exc_info[
                1
            ].with_traceback(  # type: ignore[union-attr]
                _dependency_exc_info[2]
            )

        def image_converter(image):
            with image.open() as image_bytes:
                img_data = image_bytes.read()
                content_type = image.content_type or "image/png"
            
            llm_client = kwargs.get("llm_client")
            llm_model = kwargs.get("llm_model")
            prompt = kwargs.get("llm_prompt", "Write a detailed caption for this image.")

            if not llm_client or not llm_model:
                b64_data = base64.b64encode(img_data).decode()
                return {
                    "src": "data:{0};base64,{1}".format(content_type, b64_data),
                    "alt": "image"
                }
            
            try:
                b64_data = base64.b64encode(img_data).decode()
                data_uri = f"data:{content_type};base64,{b64_data}"
                
                messages = [
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": data_uri}}
                        ]
                    }
                ]
                
                response = llm_client.chat.completions.create(
                    model=llm_model,
                    messages=messages
                )
                description = response.choices[0].message.content
                
                return {
                    "src": "data:{0};base64,{1}".format(image.content_type, b64_data),
                    "alt": description
                }
                
            except Exception as e:
                return {
                    "src": "data:{0};base64,{1}".format(image.content_type, b64_data),
                    "alt": "LLM Description failed"
                }

        style_map = kwargs.get("style_map", None)
        pre_process_stream = pre_process_docx(file_stream)
        
        html_result = mammoth.convert_to_html(
            pre_process_stream,
            style_map=style_map,
            convert_image=mammoth.images.img_element(image_converter)
        )
        
        return self._html_converter.convert_string(
            html_result.value,
            **kwargs,
        )
