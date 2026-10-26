import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

u = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16"
resp = Fetcher.get(u)
print("Default view p1 pagination links:")
for a in resp.css('ul.pagination a'):
    print(a.text.strip(), "->", a.attrib.get('href'))
