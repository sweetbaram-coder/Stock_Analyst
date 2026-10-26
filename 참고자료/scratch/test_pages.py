import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

for p in [1, 2, 3]:
    # Try with page parameter
    u = f"https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm&page={p}"
    pg = Fetcher.get(u)
    cnt = len(pg.css('ul.type2 > li'))
    print(f"page={p} without total: count={cnt}")
    
    # Try pager link style
    u_pager = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
    pg_pager = Fetcher.get(u_pager)
    cnt_pager = len(pg_pager.css('ul.type2 > li'))
    print(f"page={p} with total: count={cnt_pager}")
