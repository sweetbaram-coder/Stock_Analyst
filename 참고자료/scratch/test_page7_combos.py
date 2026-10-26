import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

candidates = [
    ("base", "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&page=7"),
    ("with_view", "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&page=7&view_type=sm"),
    ("page_first", "https://news.einfomax.co.kr/news/articleList.html?page=7&sc_section_code=S1N16"),
    ("page_first_view", "https://news.einfomax.co.kr/news/articleList.html?page=7&sc_section_code=S1N16&view_type=sm"),
    ("with_total", "https://news.einfomax.co.kr/news/articleList.html?page=7&total=185120&sc_section_code=S1N16&view_type=sm"),
]

for name, u in candidates:
    p = Fetcher.get(u)
    title = p.css('title::text')[0].text.strip() if p.css('title::text') else ''
    c2 = len(p.css('ul.type2 > li'))
    c1 = len(p.css('ul.type1 > li'))
    print(f"[{name}] title='{title}' | c2={c2} | c1={c1}")
