import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime


BASE_URL = "https://www.thairath.co.th"
NEWS_URL = f"{BASE_URL}/news/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def scrape_article_details(article_url):
    try:
      detail_res = requests.get(article_url, headers=HEADERS)
      detail_soup = BeautifulSoup(detail_res.content, "html.parser")
      body_container = detail_soup.select_one("div.css-nh9sg4.evs3ejl67")
      if not body_container:
          body_container = detail_soup.select_one("div[itemprop='articleBody']") 
      print(body_container)
      content = body_container.get_text("\n", strip=True) if body_container else "N/A"

      timestamp_tag = detail_soup.select_one("div.css-4rs0jl.e1qfz2z0")
      timestamp = timestamp_tag.get_text(strip=True) if timestamp_tag else "N/A"

      # Tags (optional)
      tags = [a.text.strip() for a in detail_soup.select("div.css-5xud4l.ev4lnf163 a")]
      
      return timestamp, content, ", ".join(tags)
    
    except Exception as e:
      print(f"❌ Failed to scrape detail from {article_url}: {e}")
      return "N/A", "N/A", "N/A"

def scrape_thairath():
    url = "https://www.thairath.co.th/news/"  # Updated URL
    response = requests.get(url, headers=HEADERS)
    print("🔄 Fetching data from", url)
    soup = BeautifulSoup(response.content, "html.parser")
    print("🔄 Parsing HTML content...")
    articles = []
    
    seen = set()
    for item in soup.select("a[href^='/news/']"):
        title_tag = item.attrs.get("title")
        link = item.attrs.get("href")
        if not title_tag or not link or link in seen:
          continue
        seen.add(link)        
        full_link = BASE_URL + link
        print("🔄 Found article:", title_tag + full_link)
        
        timestamp, content, tags = scrape_article_details(full_link)
        
        articles.append({
            "title": title_tag,
            "url": full_link,
            "scraped_at": datetime.now().isoformat(),
            "published": timestamp,
            "content": content,
            "tags": ", ".join(tags)
        })

    df = pd.DataFrame(articles)
    df.to_csv("thairath_news.csv", index=False)
    print("✅ Saved", len(df), "articles.")

def main():
    scrape_thairath()
    
if __name__ == "__main__":
    main()