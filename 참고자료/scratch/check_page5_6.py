import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

u = "https://news.einfomax.co.kr/news/articleList.html?page=5&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
page = Fetcher.get(u)
pager = page.css('ul.pagination li a')
print("Page 5 pager links:")
for a in pager:
    print(a.text.strip(), "->", a.attrib.get('href'))

u6 = "https://news.einfomax.co.kr/news/articleList.html?page=6&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
p6 = Fetcher.get(u6)
print("Page 6 ul.type2 count:", len(p6.css('ul.type2 > li')))
print("Page 6 ul.type1 count:", len(p6.css('ul.type1 > li')))
print("Page 6 title:", p6.css('title::text')[0].text.strip() if p6.css('title::text') else '')
