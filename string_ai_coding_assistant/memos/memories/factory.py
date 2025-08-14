from typing import Any, ClassVar

from string_ai_coding_assistant.memos.configs.memory import MemoryConfigFactory
from string_ai_coding_assistant.memos.memories.activation.base import BaseActMemory
from string_ai_coding_assistant.memos.memories.activation.kv import KVCacheMemory
from string_ai_coding_assistant.memos.memories.base import BaseMemory
from string_ai_coding_assistant.memos.memories.parametric.base import BaseParaMemory
from string_ai_coding_assistant.memos.memories.parametric.lora import LoRAMemory
from string_ai_coding_assistant.memos.memories.textual.base import BaseTextMemory
from string_ai_coding_assistant.memos.memories.textual.general import GeneralTextMemory
from string_ai_coding_assistant.memos.memories.textual.naive import NaiveTextMemory
from string_ai_coding_assistant.memos.memories.textual.tree import TreeTextMemory


class MemoryFactory(BaseMemory):
    """Factory class for creating memory instances."""

    backend_to_class: ClassVar[dict[str, Any]] = {
        "naive_text": NaiveTextMemory,
        "general_text": GeneralTextMemory,
        "tree_text": TreeTextMemory,
        "kv_cache": KVCacheMemory,
        "lora": LoRAMemory,
    }

    @classmethod
    def from_config(
        cls, config_factory: MemoryConfigFactory
    ) -> BaseTextMemory | BaseActMemory | BaseParaMemory:
        backend = config_factory.backend
        if backend not in cls.backend_to_class:
            raise ValueError(f"Invalid backend: {backend}")
        memory_class = cls.backend_to_class[backend]
        return memory_class(config_factory.config)
