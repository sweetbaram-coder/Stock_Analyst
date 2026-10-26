import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

u1 = 'https://news.einfomax.co.kr/news/articleList.html?page=2&sc_section_code=S1N16&view_type=sm'
p1 = Fetcher.get(u1)
print("u1 items:", len(p1.css('ul.type2 > li')))

u2 = 'https://news.einfomax.co.kr/news/articleList.html?page=2&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm'
p2 = Fetcher.get(u2)
print("u2 items:", len(p2.css('ul.type2 > li')))
if p2.css('ul.type2 > li'):
    print("u2 first item title:", p2.css('ul.type2 > li h4.titles a')[0].text.strip())
