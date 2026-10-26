import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
import urllib.parse

base = "https://news.einfomax.co.kr"
current_url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"

print("Following pagination links naturally...")
for page_num in range(1, 30):
    resp = Fetcher.get(current_url)
    items = resp.css('ul.type2 > li')
    if not items:
        print(f"Page {page_num}: No items at {current_url}")
        break
        
    first_title = items[0].css('h4.titles a')[0].text.strip()
    first_date = items[0].css('span.byline em:last-of-type')[0].text.strip()
    last_date = items[-1].css('span.byline em:last-of-type')[0].text.strip()
    print(f"Page {page_num:2d}: [{first_date} ~ {last_date}] (items: {len(items)}) First={first_title[:20]}")
    
    if last_date < "2026.08.31":
        print(f"-> 5 days ago limit reached at page {page_num} ({last_date})")
        break
        
    # Find next page link in pagination
    next_page_num = page_num + 1
    next_url = None
    
    # 1. Look for numeric link equal to next_page_num
    for a in resp.css('ul.pagination a'):
        txt = a.text.strip()
        if txt == str(next_page_num):
            next_url = urllib.parse.urljoin(base, a.attrib.get('href'))
            break
            
    # 2. If not found by number (e.g. at 10 -> 11), look for pagination-onenext or next button
    if not next_url:
        next_btn = resp.css('li.pagination-onenext a, li.pagination-next a')
        if next_btn:
            next_url = urllib.parse.urljoin(base, next_btn[0].attrib.get('href'))
            
    if not next_url:
        print(f"No next page link found at page {page_num}")
        break
        
    current_url = next_url
