from typing import List

import requests
from bs4 import BeautifulSoup
from ddgs import DDGS
from langchain.tools import StructuredTool

from system_agent.config import (
    WEB_CONTENT_LIMIT,
    WEB_LINKS_LIMIT,
    WEB_REQUEST_TIMEOUT,
    WEB_USER_AGENT,
)


class WebScraper:
    """Handles web scraping operations"""

    @staticmethod
    def scrape_url(url: str) -> str:
        """Scrape content from a URL.

        Args:
            url: The URL to scrape content from

        Returns:
            str: The scraped content or an error message
        """
        """Scrape content from a URL"""
        try:
            headers = {"User-Agent": WEB_USER_AGENT}
            response = requests.get(url, headers=headers, timeout=WEB_REQUEST_TIMEOUT)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = " ".join(chunk for chunk in chunks if chunk)

            if len(text) > WEB_CONTENT_LIMIT:
                text = text[:WEB_CONTENT_LIMIT] + "...\n[Content truncated]"

            return f"Successfully scraped '{url}':\n{text}"
        except requests.RequestException as e:
            return f"Error scraping URL '{url}': {str(e)}"
        except Exception as e:
            return f"Error processing content from '{url}': {str(e)}"

    @staticmethod
    def extract_links(url: str) -> str:
        """Extract all links from a webpage.

        Args:
            url: The URL to extract links from

        Returns:
            str: A formatted string containing the links or an error message
        """
        """Extract all links from a webpage"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"  # noqa
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")
            links = []

            for link in soup.find_all("a", href=True):
                href = link["href"]
                text = link.text.strip()
                if href.startswith("http") or href.startswith("//"):
                    links.append(f"{text}: {href}")

            if links:
                return f"Links found on '{url}':\n" + "\n".join(links[:WEB_LINKS_LIMIT])
            else:
                return f"No links found on '{url}'"
        except Exception as e:
            return f"Error extracting links from '{url}': {str(e)}"

    @staticmethod
    def duckduckgo_search(
        query: str, max_results: int = 5, search_type: str = "text"
    ) -> str:
        """
        Search DuckDuckGo for text, images, videos, or news.
        """
        try:
            max_results = max(1, min(int(max_results), 20))  # Clamp between 1 and 20
            with DDGS() as ddgs:
                search_type = search_type.lower()
                if search_type == "images":
                    results = list(ddgs.images(query, max_results=max_results))
                    return "\n".join(
                        [f"{i+1}. {r['image']}" for i, r in enumerate(results)]
                    )

                elif search_type == "videos":
                    results = list(ddgs.videos(query, max_results=max_results))
                    return "\n".join(
                        [
                            f"{i+1}. {r['title']}\n{r['url']}"
                            for i, r in enumerate(results)
                        ]
                    )

                elif search_type == "news":
                    results = list(ddgs.news(query, max_results=max_results))
                    return "\n".join(
                        [
                            f"{i+1}. {r['title']}\n{r['url']}"
                            for i, r in enumerate(results)
                        ]
                    )

                else:  # text search
                    results = list(ddgs.text(query, max_results=max_results))
                    return "\n".join(
                        [
                            f"{i+1}. {r.get('title', 'No title')}\n{r.get('href', '#')}\n{r.get('body', 'No description')}"  # noqa
                            for i, r in enumerate(results)
                        ]
                    )
        except Exception as e:
            return f"Error performing search: {str(e)}"

    def get_tools(self) -> List[StructuredTool]:
        """Return a list of StructuredTool objects for web scraping operations."""
        return [
            StructuredTool.from_function(
                name="scrape_url",
                func=self.scrape_url,
                args_schema={
                    "url": {
                        "type": "string",
                        "description": "The URL to scrape content from",
                    }
                },
                description="""Scrape content from a URL.
                Example:
                {
                    "url": "https://example.com"
                }""",
            ),
            StructuredTool.from_function(
                name="extract_links",
                func=self.extract_links,
                args_schema={
                    "url": {
                        "type": "string",
                        "description": "The URL to extract links from",
                    }
                },
                description="""Extract all links from a webpage.
                Example:
                {
                    "url": "https://example.com"
                }""",
            ),
            StructuredTool.from_function(
                name="duckduckgo_search",
                func=self.duckduckgo_search,
                args_schema={
                    "query": {"type": "string", "description": "Search query"},
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of results to return",
                    },
                    "search_type": {
                        "type": "string",
                        "description": "Type of search (text, images, videos, news)",
                    },
                },
                description="""Search the web using DuckDuckGo.
                You have to make a better query to get better results.
                You can search for text, images, videos, or news.
                Example:
                {
                    "query": "search terms",
                    "max_results": 5,
                    "search_type": "text"
                }""",
            ),
        ]
