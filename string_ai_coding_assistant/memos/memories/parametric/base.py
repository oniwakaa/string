################################################################
# TODO:
# This file currently serves as a placeholder.
# The actual implementation will be added here in the future.
# Please do not use this as a functional module yet.
################################################################

from abc import abstractmethod

from string_ai_coding_assistant.memos.configs.memory import BaseParaMemoryConfig
from string_ai_coding_assistant.memos.memories.base import BaseMemory


class BaseParaMemory(BaseMemory):
    """Base class for all parametric memory implementations."""

    @abstractmethod
    def __init__(self, config: BaseParaMemoryConfig):
        """Initialize memory with the given configuration."""
