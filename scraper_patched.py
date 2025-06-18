import requests
from bs4 import BeautifulSoup

def scrape_website_text(url):
    print(f"[SCRAPER] Fetching {url}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        texts = soup.stripped_strings
        return '\n'.join(texts)
    except Exception as e:
        return f"Error scraping {url}: {e}"