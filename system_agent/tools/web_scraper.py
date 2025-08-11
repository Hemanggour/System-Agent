import requests
from bs4 import BeautifulSoup


class WebScraper:
    """Handles web scraping operations"""
    
    @staticmethod
    def scrape_url(url: str) -> str:
        """Scrape content from a URL"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
            
            # Get text content
            text = soup.get_text()
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Limit text length to avoid overwhelming the model
            if len(text) > 5000:
                text = text[:5000] + "...\n[Content truncated]"
            
            return f"Successfully scraped '{url}':\n{text}"
        except requests.RequestException as e:
            return f"Error scraping URL '{url}': {str(e)}"
        except Exception as e:
            return f"Error processing content from '{url}': {str(e)}"
    
    @staticmethod
    def extract_links(url: str) -> str:
        """Extract all links from a webpage"""
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            links = []
            
            for link in soup.find_all('a', href=True):
                href = link['href']
                text = link.text.strip()
                if href.startswith('http') or href.startswith('//'):
                    links.append(f"{text}: {href}")
            
            if links:
                return f"Links found on '{url}':\n" + "\n".join(links[:20])  # Limit to first 20 links
            else:
                return f"No links found on '{url}'"
        except Exception as e:
            return f"Error extracting links from '{url}': {str(e)}"
