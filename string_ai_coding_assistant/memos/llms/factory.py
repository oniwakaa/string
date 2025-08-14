from typing import Any, ClassVar

from string_ai_coding_assistant.memos.configs.llm import LLMConfigFactory
from string_ai_coding_assistant.memos.llms.base import BaseLLM
from string_ai_coding_assistant.memos.llms.gguf import GGUFLLLM
from string_ai_coding_assistant.memos.llms.hf import HFLLM
from string_ai_coding_assistant.memos.llms.ollama import OllamaLLM
from string_ai_coding_assistant.memos.llms.openai import OpenAILLM


class LLMFactory(BaseLLM):
    """Factory class for creating LLM instances."""

    backend_to_class: ClassVar[dict[str, Any]] = {
        "openai": OpenAILLM,
        "ollama": OllamaLLM,
        "huggingface": HFLLM,
        "gguf": GGUFLLLM,
    }

    @classmethod
    def from_config(cls, config_factory: LLMConfigFactory) -> BaseLLM:
        backend = config_factory.backend
        if backend not in cls.backend_to_class:
            raise ValueError(f"Invalid backend: {backend}")
        llm_class = cls.backend_to_class[backend]
        return llm_class(config_factory.config)
