import sys
sys.path.append('scripts')
from scrapling.fetchers import FetcherSession

session = FetcherSession()

print("Testing with FetcherSession...")
for p in range(1, 10):
    if p == 1:
        u = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
    else:
        u = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
    
    resp = session.get(u)
    title = resp.css('title::text')[0].text.strip() if resp.css('title::text') else ''
    cnt2 = len(resp.css('ul.type2 > li'))
    cnt1 = len(resp.css('ul.type1 > li'))
    print(f"Page {p}: Title='{title}' | ul.type2={cnt2} | ul.type1={cnt1}")
