import os

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from serpapi import GoogleSearch

load_dotenv()

def is_cmu_africa_relevant(text: str) -> bool:
    """Check if the text content is relevant to cmu-africa"""
    cmu_africa_keywords = [
        "rwanda", "kigali", "rw", "cmu-africa"
    ]
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in cmu_africa_keywords)


def google_search(query: str, num_results: int = 3, add_cmu_africa_context: bool = True) -> str:
    """
    Perform a CMU-Africa-specific Google search using SerpAPI
    
    Args:
        query: Search query
        num_results: Number of results to return
        add_cmu_africa_context: Whether to automatically add CMU-Africa to the query
    
    Returns:
        Combined text snippets from search results
    """
    api_key = os.getenv("SERPAPI_API_KEY")
    if not api_key:
        raise ValueError("Please set the SERPAPI_API_KEY environment variable.")

    # Automatically add cmu-africa context to queries if not present
    if add_cmu_africa_context and "cmu-africa" not in query.lower():
        query = f"{query} cmu-africa"

    # CMU-Africa-specific search parameters
    search_params = {
        "q": query,
        "api_key": api_key,
        "num": num_results * 2,  # Get more results to filter for relevance
        "gl": "rw",              # Rwanda country code
        "location": "Rwanda",    # Geographic targeting
        "hl": "en"              # Language preference)
    }
    
    search = GoogleSearch(search_params)
    results = search.get_dict()
    snippets = []
    
    for res in results.get("organic_results", []):
        link = res.get("link", "")
        snippet = extract_page_text(link)
        
        # Only include CMU-Africa-relevant content
        if snippet and is_cmu_africa_relevant(snippet):
            snippets.append(snippet)
            
        # Stop when we have enough relevant results
        if len(snippets) >= num_results:
            break
    
    # If we don't have enough CMU-Africa-specific results, fall back to all results
    if len(snippets) < num_results:
        for res in results.get("organic_results", []):
            if len(snippets) >= num_results:
                break
            link = res.get("link", "")
            snippet = extract_page_text(link)
            if snippet and snippet not in snippets:
                snippets.append(snippet)
    
    return "\n\n".join(snippets)

def extract_page_text(url: str) -> str:
    try:
        response = requests.get(url, timeout=10)
        soup = BeautifulSoup(response.text, "html.parser")
        return soup.get_text()[:2000]  # Trim long pages
    except Exception:
        return ""


def is_answer_unavailable(answer: str) -> bool:
    keywords = [
        "not available",
        "not in the context",
        "i'm sorry",
        "i am sorry",
        "no information",
        "can't answer",
        "cannot answer",
        "insufficient context",
        "don't have information",
        "unable to find",
        "the text does not provide"
    ]
    return any(kw in answer.lower() for kw in keywords)