from markitdown import MarkItDown

from string_ai_coding_assistant.memos.configs.parser import MarkItDownParserConfig
from string_ai_coding_assistant.memos.log import get_logger
from string_ai_coding_assistant.memos.parsers.base import BaseParser


logger = get_logger(__name__)


class MarkItDownParser(BaseParser):
    """MarkItDown Parser class."""

    def __init__(self, config: MarkItDownParserConfig):
        self.config = config

    def parse(self, file_path: str) -> str:
        """Parse the file at the given path and return its content as a MarkDown string."""
        md = MarkItDown(enable_plugins=False)
        result = md.convert(file_path)

        return result.text_content
