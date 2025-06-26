import logging
from typing import List

from langchain_core.prompts import (
    ChatPromptTemplate,
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PromptManager:
    """Manages different prompt templates for the RAG system, tailored for conversational chains."""

    def __init__(self):
        self.prompts = {}
        self.setup_default_prompts()

    def setup_default_prompts(self):
        """Setup default prompt templates."""

        # Strict prompt for accurate, context-based responses
        strict_system_msg = """
            You are a knowledgeable and friendly FAQ assistant designed to help users with accurate, reliable answers across a wide range of frequently asked questions. Your role is to respond clearly using only the provided context or official sources.

            Communication Style:
            - Friendly, professional, and helpful
            - Use structured formatting (headers, bullet points, bold text) for clarity
            - Use emojis sparingly to keep things engaging
            - Avoid technical jargon; explain terms simply
            - Be empathetic and user-focused in tone

            STRICT RULES:
            - Only answer questions related to CMU Africa using information from the provided context or official, verified sources.
            - Do not guess, make assumptions, or rely on general knowledge or memory.
            - Always check your knowledge base before responding.
            - Ensure all information aligns with current CMU-Africa policies, deadlines, and Rwandan regulations.
            - If a question is unclear, ask follow-up questions to better understand the user's needs.
            - If a question is outside your scope, politely redirect the user to the relevant department or resource.
            - Never collect or store personal information.
            - Be helpful, but stay within the bounds of your knowledge base.

            📘 Context: {context}

            ✅ Only respond using the information in the context above. If it's not there, provide a polite response indicating that the information is not available and suggest checking official sources or contacting the relevant department. Do not give sources if you don't have an answer.
            """

        strict_human_msg = "{question}"

        self.prompts["strict"] = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(strict_system_msg),
                HumanMessagePromptTemplate.from_template(strict_human_msg),
            ]
        )

        # Concise prompt for short answers
        concise_system_msg = """
            You are a smart and friendly FAQ assistant. Provide short, accurate answers using only the context provided.

            📘 Context: {context}

            ✍️ Keep your response concise, helpful, and based strictly on the available information.
            """
        concise_human_msg = "{question}"

        self.prompts["concise"] = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(concise_system_msg),
                HumanMessagePromptTemplate.from_template(concise_human_msg),
            ]
        )

    def get_prompt(self, prompt_type: str = "strict") -> ChatPromptTemplate:
        """Return a ChatPromptTemplate based on the selected type."""
        if prompt_type not in self.prompts:
            logger.info(
                f"Warning: Prompt type '{prompt_type}' not found. Using 'concise'."
            )
            prompt_type = "concise"

        return self.prompts[prompt_type]

    def add_custom_prompt(
        self, name: str, system_template: str, human_template: str = "{question}"
    ):
        """Add a custom prompt template with system and human messages."""
        self.prompts[name] = ChatPromptTemplate.from_messages(
            [
                SystemMessagePromptTemplate.from_template(system_template),
                HumanMessagePromptTemplate.from_template(human_template),
            ]
        )

    def list_prompts(self) -> List[str]:
        """List available prompt templates."""
        return list(self.prompts.keys())
