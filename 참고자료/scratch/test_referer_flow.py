import sys
sys.path.append('scripts')
from scrapling.fetchers import FetcherSession

with FetcherSession() as s:
    prev_url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
    resp = s.get(prev_url)
    print("P1 title:", resp.css('title::text')[0].text.strip())
    
    for p in range(2, 12):
        curr_url = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
        resp = s.get(curr_url, headers={"Referer": prev_url})
        t = resp.css('title::text')[0].text.strip() if resp.css('title::text') else ''
        c2 = len(resp.css('ul.type2 > li'))
        c1 = len(resp.css('ul.type1 > li'))
        print(f"P{p}: title='{t}' | c2={c2} | c1={c1}")
        if c2 > 0:
            first_date = resp.css('ul.type2 > li span.byline em:last-of-type')[0].text.strip()
            print(f"    first_date: {first_date}")
        prev_url = curr_url
