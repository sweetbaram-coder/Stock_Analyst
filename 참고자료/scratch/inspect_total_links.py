from scrapling.fetchers import Fetcher
import re

p1_url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
p1 = Fetcher.get(p1_url)
links = p1.css('a[href*="total="]')
print(f"Found {len(links)} links with total=")
for idx, l in enumerate(links):
    href = l.attrib.get('href', '')
    print(f"[{idx}] text='{l.text.strip()}' href='{href}'")
