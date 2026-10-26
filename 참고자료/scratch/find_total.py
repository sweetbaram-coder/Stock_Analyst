import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
import re

url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
page = Fetcher.get(url)

with open('scratch/page1.html', 'w', encoding='utf-8') as f:
    f.write(page.html_content)

# Search for total numbers or counts in page
totals = re.findall(r'total[^\d]*(\d+)', page.html_content, re.IGNORECASE)
print("Regex total matches:", set(totals))

# Search for text like "총 N건" or "전체 N건"
counts = re.findall(r'(\d[\d,]*)\s*건', page.html_content)
print("Matches with '건':", counts)
