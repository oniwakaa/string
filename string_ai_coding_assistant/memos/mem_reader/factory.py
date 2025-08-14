from typing import Any, ClassVar

from string_ai_coding_assistant.memos.configs.mem_reader import MemReaderConfigFactory
from string_ai_coding_assistant.memos.mem_reader.base import BaseMemReader
from string_ai_coding_assistant.memos.mem_reader.simple_struct import SimpleStructMemReader


class MemReaderFactory(BaseMemReader):
    """Factory class for creating MemReader instances."""

    backend_to_class: ClassVar[dict[str, Any]] = {
        "simple_struct": SimpleStructMemReader,
    }

    @classmethod
    def from_config(cls, config_factory: MemReaderConfigFactory) -> BaseMemReader:
        backend = config_factory.backend
        if backend not in cls.backend_to_class:
            raise ValueError(f"Invalid backend: {backend}")
        reader_class = cls.backend_to_class[backend]
        return reader_class(config_factory.config)
