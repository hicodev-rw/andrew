import logging
from typing import List

from langchain.chains import ConversationalRetrievalChain
from langchain_openai import ChatOpenAI

from src.core.prompt_manager import PromptManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class QAChainManager:
    """Manages different types of QA chains"""

    def __init__(self, llm: ChatOpenAI, prompt_manager: PromptManager):
        self.llm = llm
        self.prompt_manager = prompt_manager
        self.chains = {}

    def create_conversational_chain(
        self,
        retriever,
        memory,
        chain_name: str = "conversational",
        prompt_type: str = "strict",
    ):
        """Create a conversational retrieval chain"""
        try:
            prompt = self.prompt_manager.get_prompt(prompt_type)

            qa_chain = ConversationalRetrievalChain.from_llm(
                llm=self.llm,
                retriever=retriever,
                memory=memory,
                return_source_documents=True,
                verbose=False,
                combine_docs_chain_kwargs={"prompt": prompt},
            )

            self.chains[chain_name] = qa_chain
            logger.info(f"Conversational chain '{chain_name}' created successfully!")
            return qa_chain

        except Exception as e:
            logger.error(f"Error creating conversational chain: {e}")
            return None

    def get_chain(self, chain_name: str = "default"):
        """Get a specific chain"""
        return self.chains.get(chain_name)

    def list_chains(self) -> List[str]:
        """List available chains"""
        return list(self.chains.keys())
