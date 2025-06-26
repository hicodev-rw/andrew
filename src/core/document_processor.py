import logging
import os
from typing import (
    Dict,
    List,
    Optional,
)

import fitz
import requests
from bs4 import BeautifulSoup
from langchain.schema import Document
from langchain_openai import OpenAIEmbeddings
from tqdm import tqdm

from src.core.store_manager import VectorStoreManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# __________________________________________________________________________

sources_file = "./src/utils/sources.txt"
store_path = "./src/store"


class DocumentProcessor:
    """Handles document loading and text extraction from various sources"""

    def __init__(self):
        self.supported_types = ["url", "file"]
        self.supported_extensions = [".pdf", ".txt"]
        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small", openai_api_key=os.getenv("OPENAI_API_KEY")
        )
        self.vectorstore_manager = VectorStoreManager(self.embeddings)

    def extract_text_from_url(self, url: str) -> str:
        """Extract text from a URL"""
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            return soup.get_text(separator="\n")
        except Exception as e:
            logger.error(f"Error extracting text from {url}: {e}")
            return ""

    def extract_text_from_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            text = ""
            with fitz.open(file_path) as pdf:
                for page in pdf:
                    text += page.get_text("text")
            return text
        except Exception as e:
            logger.error(f"Error extracting text from PDF {file_path}: {e}")
            return ""

    def extract_text_from_txt(self, file_path: str) -> str:
        """Extract text from text file"""
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()
        except Exception as e:
            logger.error(f"Error extracting text from text file {file_path}: {e}")
            return ""

    def load_sources_from_file(self, file_path: str) -> List[Dict[str, str]]:
        """Load sources from configuration file"""
        sources = []
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                for line_num, line in enumerate(file, 1):
                    line = line.strip()
                    if not line or line.startswith(
                        "#"
                    ):  # Skip empty lines and comments
                        continue

                    parts = line.split(", ")
                    if len(parts) >= 2:
                        source_type = parts[0].strip()
                        path = ", ".join(parts[1:]).strip()  # Handle paths with commas

                        if source_type in self.supported_types:
                            sources.append({"type": source_type, "path": path})
                        else:
                            logger.info(
                                f"Warning: Unsupported source type '{source_type}' on line {line_num}"
                            )
                    else:
                        logger.info(
                            f"Warning: Invalid format on line {line_num}: {line}"
                        )
        except Exception as e:
            logger.error(f"Error loading sources from {file_path}: {e}")

        return sources

    def process_document(self, source: Dict[str, str]) -> Optional[Document]:
        """Process a single document source"""
        try:
            text = ""
            source_type = source["type"]
            path = source["path"]

            if source_type == "url":
                text = self.extract_text_from_url(path)
            elif source_type == "file":
                if path.endswith(".pdf"):
                    text = self.extract_text_from_pdf(path)
                elif path.endswith(".txt"):
                    text = self.extract_text_from_txt(path)
                else:
                    logger.info(f"Unsupported file extension: {path}")
                    return None

            if text.strip():
                return Document(
                    page_content=text,
                    metadata={"source": path, "type": source_type, "length": len(text)},
                )
            else:
                logger.info(f"No text extracted from {path}")
                return None

        except Exception as e:
            logger.error(f"Error processing document {source}: {e}")
            return None

    def load_documents(self, sources: List[Dict[str, str]]) -> List[Document]:
        """Load and process documents from multiple sources"""
        documents = []

        # Use tqdm tto show progress
        for source in tqdm(sources, desc="Processing sources", unit="source"):
            doc = self.process_document(source)
            if doc:
                documents.append(doc)

        return documents

    def ingest_and_save_sources(self, sources_file: str, store_path: str) -> bool:
        """
        Load documents from sources file, embed them into FAISS, and save the index to disk.
        Returns True on success.
        """
        try:
            sources = self.load_sources_from_file(sources_file)
            if not sources:
                logger.info("No sources found!")
                return False

            docs = self.load_documents(sources)
            if not docs:
                logger.info("No documents processed!")
                return False

            if not self.vectorstore_manager.create_vectorstore(docs):
                logger.info("Failed to build vectorstore!")
                return False

            self.vectorstore_manager.save_vectorstore(store_path)
            return True

        except Exception as e:
            logger.error(f"Error ingesting sources: {e}")
            return False


# initialize the DocumentProcessor
document_processor = DocumentProcessor()

# load sources from a configuration file and save content to the vector store
document_processor.ingest_and_save_sources(sources_file, store_path)
