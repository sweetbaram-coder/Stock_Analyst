import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

for p in range(1, 10):
    url = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
    page = Fetcher.get(url)
    items = page.css('ul.type2 > li')
    if not items:
        print(f"Page {p}: No items")
        break
    
    first_title = items[0].css('h4.titles a')[0].text.strip()
    first_date = items[0].css('span.byline em:last-of-type')[0].text.strip()
    last_title = items[-1].css('h4.titles a')[0].text.strip()
    last_date = items[-1].css('span.byline em:last-of-type')[0].text.strip()
    
    print(f"Page {p} (count: {len(items)}): First=[{first_date}] {first_title[:20]} | Last=[{last_date}] {last_title[:20]}")
