import logging
import os
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from tqdm import tqdm

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

file_path = "./src/utils/sources.txt"
folder_path = "./sources" # path to the folder containing text files

def add_files_to_sources(folder_path, file_path):
    try:
        with open(file_path, "a") as f:
            for filename in os.listdir(folder_path):
                file_path = f"{folder_path}/{filename}"

                f.write(f"file, {file_path}\n")
                logger.info(f"Added {file_path} to sources.txt")
    except Exception as e:
        logger.error(f"Error adding files to sources: {e}")

def scrape_subpages(main_url):
    # Request the main page
    response = requests.get(main_url)
    if response.status_code != 200:
        logger.error(f"Failed to access {main_url}")
        return

    soup = BeautifulSoup(response.text, "html.parser")

    # Find all links on the page
    links = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"]
        # Convert relative URLs to absolute URLs
        full_url = urljoin(main_url, href)

        # Optional: only keep links within the same domain
        if urlparse(full_url).netloc == urlparse(main_url).netloc:
            links.add(full_url)

    logger.info(f"Found {len(links)} subpages.")

    # Visit each subpage and print the title
    for link in tqdm(links, desc="Processing sources", unit="source"):
        try:
            r = requests.get(link)
            if r.status_code == 200:

                # save the url to a csv file
                with open(file_path, "a") as f:
                    # Write the link to the CSV file
                    f.write(f"url, {link} \n")
            else:
                logger.warning(f"Failed to access {link}")
        except Exception as e:
            logger.error(f"Error accessing {link}: {e}")


scrape_subpages("https://www.africa.engineering.cmu.edu/")
logger.info("Scraping completed. Now adding local text files to sources.txt")
add_files_to_sources(folder_path, file_path)
