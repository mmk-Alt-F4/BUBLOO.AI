import os
from urllib.parse import urlparse, urljoin
import time

def scrape_website(base_url, output_file="knowledge_base/scraped_content.txt", max_pages=30):
    """Scrape content from the whole website starting from base_url, following internal links."""
    try:
        import requests
        from bs4 import BeautifulSoup
    except ImportError as e:
        return False, f"Missing dependencies: {e}. Please run `pip install beautifulsoup4 requests`."

    try:
        print(f"Starting scrape of {base_url} (Max pages: {max_pages})...")
        
        domain = urlparse(base_url).netloc
        visited = set()
        queue = [base_url]
        all_content = []
        
        # Create output directory if it doesn't exist
        os.makedirs(os.path.dirname(output_file), exist_ok=True)

        while queue and len(visited) < max_pages:
            current_url = queue.pop(0)
            
            # Clean URL (remove fragments and query params for deduplication)
            clean_url = current_url.split('#')[0]
            if clean_url in visited:
                continue
                
            try:
                print(f"Scraping: {current_url}")
                response = requests.get(current_url, timeout=10)
                if response.status_code != 200:
                    print(f"Skipping {current_url}: Status {response.status_code}")
                    continue
                
                # Only scrape HTML
                content_type = response.headers.get('Content-Type', '')
                if 'text/html' not in content_type:
                    print(f"Skipping {current_url}: Not HTML ({content_type})")
                    continue

                visited.add(clean_url)
                soup = BeautifulSoup(response.content, 'html.parser')

                # Extract content (headers, paragraphs, list items)
                text_elements = soup.find_all(['h1', 'h2', 'h3', 'p', 'li'])
                page_text = "\n".join([elem.get_text().strip() for elem in text_elements if elem.get_text().strip()])
                
                if page_text:
                    all_content.append(f"\n\n{'='*50}\nURL: {current_url}\n{'='*50}\n{page_text}")
                
                # Find internal links
                for link in soup.find_all('a', href=True):
                    href = link['href']
                    full_url = urljoin(current_url, href)
                    parsed_link = urlparse(full_url)
                    
                    # Only follow internal links
                    if parsed_link.netloc == domain:
                        clean_link = full_url.split('#')[0]
                        if clean_link not in visited and clean_link not in queue:
                            queue.append(clean_link)
                            
                # Be polite
                time.sleep(0.5)
                
            except Exception as e:
                print(f"Error scraping {current_url}: {e}")
                continue

        if not all_content:
            return False, "No content found or scraping failed."

        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"Scrape Base URL: {base_url}\n")
            f.write(f"Total Pages Scraped: {len(visited)}\n")
            f.write("\n".join(all_content))
            
        return True, f"Successfully scraped {len(visited)} pages to {output_file}"

    except Exception as e:
        print(f"Global error scraping {base_url}: {e}")
        return False, str(e)

if __name__ == "__main__":
    # Example usage
    url = input("Enter the URL to scrape: ")
    scrape_website(url)
