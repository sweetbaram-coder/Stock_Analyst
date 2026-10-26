import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url7 = "https://news.einfomax.co.kr/news/articleList.html?page=7&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
p7 = Fetcher.get(url7)
print("P7 status:", p7.status)
print("P7 title:", p7.css('title::text')[0].text.strip() if p7.css('title::text') else '')
print("ul.type2 count:", len(p7.css('ul.type2 > li')))
print("ul.type1 count:", len(p7.css('ul.type1 > li')))
if p7.css('ul.type2 > li'):
    d = p7.css('ul.type2 > li span.byline em:last-of-type')[0].text.strip()
    print("P7 first date:", d)
