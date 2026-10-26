import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
from datetime import datetime

base_url = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm&page={}'

print("Testing pagination and dates...")
for p in range(1, 15):
    url = base_url.format(p)
    page = Fetcher.get(url)
    items = page.css('ul.type2 > li')
    if not items:
        print(f"Page {p}: No items")
        break
    
    first_date = items[0].css('span.byline em:last-of-type')
    last_date = items[-1].css('span.byline em:last-of-type')
    
    fd = first_date[0].text.strip() if first_date else 'N/A'
    ld = last_date[0].text.strip() if last_date else 'N/A'
    
    print(f"Page {p} (items {len(items)}): First={fd}, Last={ld}")
