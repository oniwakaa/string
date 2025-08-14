import openai

from string_ai_coding_assistant.memos.configs.llm import OpenAILLMConfig
from string_ai_coding_assistant.memos.llms.base import BaseLLM
from string_ai_coding_assistant.memos.llms.utils import remove_thinking_tags
from string_ai_coding_assistant.memos.log import get_logger
from string_ai_coding_assistant.memos.types import MessageList


logger = get_logger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI LLM class."""

    def __init__(self, config: OpenAILLMConfig):
        self.config = config
        self.client = openai.Client(api_key=config.api_key, base_url=config.api_base)

    def generate(self, messages: MessageList) -> str:
        """Generate a response from OpenAI LLM."""
        response = self.client.chat.completions.create(
            model=self.config.model_name_or_path,
            messages=messages,
            extra_body=self.config.extra_body,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
            top_p=self.config.top_p,
        )
        logger.info(f"Response from OpenAI: {response.model_dump_json()}")
        response_content = response.choices[0].message.content
        if self.config.remove_think_prefix:
            return remove_thinking_tags(response_content)
        else:
            return response_content
