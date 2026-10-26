import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

for p in range(1, 15):
    u = f"https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&page={p}"
    # Wait, what if we use the default view or check pagination links from default view?
    if p == 1:
        u = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16"
    resp = Fetcher.get(u)
    t = resp.css('title::text')[0].text.strip() if resp.css('title::text') else ''
    c1 = len(resp.css('ul.type1 > li'))
    c2 = len(resp.css('ul.type2 > li'))
    print(f"p={p} (default view): title='{t}' | c1={c1} | c2={c2}")
