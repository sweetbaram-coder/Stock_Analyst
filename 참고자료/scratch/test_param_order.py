import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

tests = [
    ("original_query", "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm&page=2"),
    ("section_first", "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&page=2&view_type=sm"),
    ("exact_pager_link", "https://news.einfomax.co.kr/news/articleList.html?page=2&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"),
]

for name, u in tests:
    page = Fetcher.get(u)
    titles = page.css('title::text')
    title = titles[0].text.strip() if titles else ''
    first_cat = page.css('ul.type2 li span.byline em:first-of-type, ul.type1 li span.byline em:first-of-type')
    cat = first_cat[0].text.strip() if first_cat else 'None'
    count = len(page.css('ul.type2 > li, ul.type1 > li'))
    print(f"[{name}] count: {count} | Title: {title} | first_cat: {cat}")
