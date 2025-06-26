import logging
from typing import List

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# __________________________________________________________________________


class VectorStoreManager:
    """Manages vector store operations"""

    def __init__(self, embeddings: OpenAIEmbeddings):
        self.embeddings = embeddings
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", " ", ""],
        )
        self.vectorstore = None

    def create_vectorstore(self, documents: List[Document]) -> bool:
        """Create vector store from documents"""
        if not documents:
            logger.info("No documents provided for vector store creation!")
            return False

        try:
            # Split documents into chunks
            split_docs = self.text_splitter.split_documents(documents)

            # Create vector store
            self.vectorstore = FAISS.from_documents(
                documents=split_docs, embedding=self.embeddings
            )

            # logger.info("Vector store created successfully!")
            return True

        except Exception as e:
            logger.error(f"Error creating vector store: {e}")
            return False

    def save_vectorstore(self, path: str) -> bool:
        """Save vector store to disk"""
        if not self.vectorstore:
            logger.info("No vector store to save!")
            return False

        try:
            self.vectorstore.save_local(path)
            logger.info(f"Vector store saved to {path}")
            return True
        except Exception as e:
            logger.error(f"Error saving vector store: {e}")
            return False

    def load_vectorstore(self, path: str) -> bool:
        """Load vector store from disk"""
        try:
            self.vectorstore = FAISS.load_local(
                path, self.embeddings, allow_dangerous_deserialization=True
            )
            return True
        except Exception as e:
            logger.error(f"Error loading vector store: {e}")
            return False

    def get_retriever(self, search_type: str = "similarity", k: int = 3):
        """Get retriever from vector store"""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized!")

        return self.vectorstore.as_retriever(
            search_type=search_type, search_kwargs={"k": k}
        )

    def similarity_search(self, query: str, k: int = 3):
        """Perform similarity search"""
        if not self.vectorstore:
            raise ValueError("Vector store not initialized!")

        return self.vectorstore.similarity_search(query, k=k)
