import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import boto3


BASE_URL = "https://www.thairath.co.th"
NEWS_URL = f"{BASE_URL}/news/"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def upload_to_s3(file_name, bucket_name, object_name=None):
  s3_client = boto3.client('s3')
  try:
    if object_name is None:
      object_name = file_name
    s3_client.upload_file(file_name, bucket_name, object_name)
    print(f"✅ Successfully uploaded {file_name} to S3 bucket {bucket_name}.")
  except Exception as e:
    print(f"❌ Failed to upload {file_name} to S3: {e}")


import json, re
from collections import deque

DATE_RE = re.compile(r"\d{1,2}\s[ก-๙]+\.\s\d{4}\s\d{1,2}:\d{2}")

def find_article_blob(obj):
    """Breadth-first search: return first dict that has 'content' & 'tags'."""
    q = deque([obj])
    while q:
        node = q.popleft()
        if isinstance(node, dict):
            if "content" in node and isinstance(node["content"], list):
                return node
            q.extend(node.values())
        elif isinstance(node, list):
            q.extend(node)
    return None    # not found
  

def clean_date(text: str) -> str:
    if not text:
        return "N/A"
    text = text.replace("\xa0", " ").strip()
    
    if text.endswith("น."):
        text = text[:-2].strip()
    return text or "N/A"

def scrape_article_details(url: str):
  try:
    res  = requests.get(url, headers=HEADERS, timeout=15)
    soup = BeautifulSoup(res.content, "html.parser")
    
    script = soup.find("script", id="__NEXT_DATA__")
    if script:
        print("Script found, ", script)
        data = json.loads(script.string)
        article = find_article_blob(data)
        if article:
          published = article.get("publishLabelThai", "N/A")

          paragraphs = [
              blk.get("data", {}).get("text", "")
              for blk in article["content"]
              if blk.get("type") == "paragraph"
          ]
          content = "\n\n".join(p.strip() for p in paragraphs if p.strip()) or "N/A"
          
          tags_elem = soup.select("div[class*='ev4lnf'] a")
          tags = ", ".join(a.get_text(strip=True) for a in tags_elem)


          return published, content, tags

    body_p = soup.select("div[itemprop='articleBody'] p") \
      or soup.select("div[class*='evs3ejl'] p")
    content = "\n\n".join(p.get_text(strip=True) for p in body_p) or "N/A"
    
    date_div   = soup.select_one('div[class*="item_article-date"]')
    published  = clean_date(date_div.get_text(" ", strip=True)) if date_div else "N/A"
    if published == "N/A":                       # last-ditch regex
      published = clean_date((soup.find(text=DATE_RE) or ""))

    tags = soup.select_one("div[class*='ev4lnf'] a")
    if tags:
      tags = ", ".join(a.get_text(strip=True) for a in tags.find_all("a"))
    else:
      tags = "N/A"


    return published, content, tags

  except Exception as e:
    print(f"❌ Failed to scrape {url}\n   {e}")
    return "N/A", "N/A", "N/A"
  
  
def scrape_thairath():
    url = "https://www.thairath.co.th/news/"
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
            "tags": tags,
        })

    df = pd.DataFrame(articles)
    df.to_csv("thairath_news.csv", index=False)
    upload_to_s3("thairath_news.csv", "kmuttcpe393datamodelnewssum", "news_summary/thairath_news.csv")
    print("✅ Saved", len(df), "articles.")

def main():
    scrape_thairath()
    
if __name__ == "__main__":
    main()