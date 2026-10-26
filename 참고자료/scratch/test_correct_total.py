import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

total = "185125"

print(f"Testing with exact total={total}...")
for p in range(1, 20):
    if p == 1:
        u = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
    else:
        u = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total={total}&box_idxno=&sc_section_code=S1N16&view_type=sm"
    
    resp = Fetcher.get(u)
    items = resp.css('ul.type2 > li')
    if not items:
        print(f"Page {p}: No items")
        break
    
    first_title = items[0].css('h4.titles a')[0].text.strip()
    first_date = items[0].css('span.byline em:last-of-type')[0].text.strip()
    last_date = items[-1].css('span.byline em:last-of-type')[0].text.strip()
    print(f"Page {p:2d}: [{first_date} ~ {last_date}] (count={len(items)}) First={first_title[:25]}")
    
    if last_date < "2026.08.31":
        print(f"-> 5 days ago limit reached at page {p} ({last_date})")
        break
