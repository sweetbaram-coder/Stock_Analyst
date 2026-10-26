import sys
sys.path.append('scripts')
from scrapling.fetchers import FetcherSession

with FetcherSession() as session:
    for p in range(1, 30):
        if p == 1:
            u = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
        else:
            # Always ensure sc_section_code and view_type are passed!
            u = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
        
        resp = session.get(u)
        items = resp.css('ul.type2 > li')
        if not items:
            print(f"Page {p}: No items")
            break
        
        d_first = items[0].css('span.byline em:last-of-type')[0].text.strip()
        d_last = items[-1].css('span.byline em:last-of-type')[0].text.strip()
        print(f"Page {p}: [{d_first} ~ {d_last}] (items: {len(items)})")
        
        # Stop condition check: earlier than 2026.08.31
        # Let's see how far it goes
        if d_last < "2026.08.31":
            print(f"Reached 5 days ago limit at page {p} ({d_last})")
            break
