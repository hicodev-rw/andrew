import logging
import os
from typing import AsyncGenerator, Dict

from dotenv import load_dotenv
from langchain.schema import Document
from langchain_openai import ChatOpenAI, OpenAIEmbeddings

from src.core.memory_manager import MemoryManager
from src.core.prompt_manager import PromptManager
from src.core.qa_chain_manager import QAChainManager
from src.core.store_manager import VectorStoreManager
from src.utils.helpers import google_search, is_answer_unavailable

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# __________________________________________________________________________

store_path = "./src/store"  # path to the vector store


class Bot:
    """Main RAG system that orchestrates all components"""

    def __init__(
        self,
        model_name: str,
        temperature: float = 0.5,
        streaming: bool = False,
    ):
        # Set vLLM API details
        vllm_base_url = "http://172.29.98.248:8000/v1"
        vllm_api_key = "mobile-edge-ai-lab-token-123"

        # Initialize core LangChain components
        self.llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            streaming=streaming,
            openai_api_base=vllm_base_url,
            openai_api_key=vllm_api_key,
        )

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Initialize component managers
        self.prompt_manager = PromptManager()
        self.memory_manager = MemoryManager(self.llm)
        self.vectorstore_manager = VectorStoreManager(self.embeddings)
        self.qa_chain_manager = QAChainManager(self.llm, self.prompt_manager)

        # Current active components
        self.current_memory = None
        self.current_chain = None

        logger.info("🎓 CMU Africa RAG System initialized successfully using vLLM!")

    def setup_from_vectorstore(
        self,
        store_path: str = store_path,
        memory_type: str = "window",
    ) -> bool:
        """Load FAISS vectorstore from disk, and QA chain."""
        try:
            self.current_memory = self.memory_manager.create_memory(memory_type)

            if not self.vectorstore_manager.load_vectorstore(store_path):
                logger.info("Failed to load vectorstore!")
                return False

            retriever = self.vectorstore_manager.get_retriever()

            self.current_chain = self.qa_chain_manager.create_conversational_chain(
                retriever, self.current_memory
            )

            return self.current_chain is not None

        except Exception as e:
            logger.error(f"Error during setup: {e}")
            return False

    async def ask_question(
        self, question: str, chain_name: str = "default"
    ) -> AsyncGenerator[Dict, None]:
        """Asks a question using the specified chain."""
        chain = self.qa_chain_manager.get_chain(chain_name) or self.current_chain

        if not chain:
            yield {
                "answer": "No QA chain available. Please run setup first.",
                "source_documents": [],
            }
            return

        try:
            inputs = (
                {"question": question}
                if "ConversationalRetrieval" in str(type(chain))
                else {"input": question}
            )

            result = chain.invoke(inputs)
            answer = result.get("answer", "")

            if is_answer_unavailable(answer):
                logger.info("🤖 Falling back to Google search...")
                google_context = google_search(question)
                fallback_prompt = f"Use the information below to answer the user's question.\n\nContext:\n{google_context}\n\nQuestion: {question}"
                fallback_answer = self.llm.invoke(fallback_prompt)

                fallback_doc = Document(
                    page_content=fallback_answer.content,
                    metadata={"source": "www.google.com, Google Search"},
                )

                yield {
                    "answer": fallback_answer.content,
                    "source_documents": [fallback_doc],
                    "fallback_used": True,
                }
            else:
                yield result

        except Exception as e:
            logger.error(f"Error during streaming: {e}")
            yield {
                "answer": "Sorry, I encountered an error processing your question.",
                "source_documents": [],
            }

    def clear_memory(self):
        """Clear conversation memory"""
        if self.current_memory:
            self.current_memory.clear()
            logger.info("Memory cleared!")
        else:
            logger.info("No active memory to clear.")

    def get_system_info(self) -> Dict:
        """Get information about the current system state"""
        return {
            "available_prompts": self.prompt_manager.list_prompts(),
            "available_chains": self.qa_chain_manager.list_chains(),
            "vectorstore_loaded": self.vectorstore_manager.vectorstore is not None,
            "memory_active": self.current_memory is not None,
            "current_chain_active": self.current_chain is not None,
        }
