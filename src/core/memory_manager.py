import logging

from langchain.memory import (
    ConversationBufferWindowMemory,
    ConversationSummaryBufferMemory,
)
from langchain_openai import ChatOpenAI

# __________________________________________________________________________

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MemoryManager:
    """Manages different types of conversation memory"""

    def __init__(self, llm: ChatOpenAI):
        self.llm = llm
        self.memory_types = {
            "window": self._create_window_memory,
            "summary": self._create_summary_memory,
            "persistent": self._create_persistent_memory,
        }

    def _create_window_memory(self, k: int = 10) -> ConversationBufferWindowMemory:
        """Create window-based memory"""
        return ConversationBufferWindowMemory(
            k=k, memory_key="chat_history", return_messages=True, output_key="answer"
        )

    def _create_summary_memory(
        self, max_tokens: int = 1000
    ) -> ConversationSummaryBufferMemory:
        """Create summary-based memory"""
        return ConversationSummaryBufferMemory(
            llm=self.llm,
            max_token_limit=max_tokens,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
        )

    def _create_persistent_memory(
        self, k: int = 10, file_path: str = "chat_history.json"
    ) -> ConversationBufferWindowMemory:
        """Create persistent file-based memory"""
        from langchain.memory import FileChatMessageHistory

        return ConversationBufferWindowMemory(
            k=k,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer",
            chat_memory=FileChatMessageHistory(file_path),
        )

    def create_memory(self, memory_type: str = "window", **kwargs):
        """Create memory of specified type"""
        if memory_type not in self.memory_types:
            logger.info(
                f"Warning: Memory type '{memory_type}' not supported. Using 'window'."
            )
            memory_type = "window"

        return self.memory_types[memory_type](**kwargs)
