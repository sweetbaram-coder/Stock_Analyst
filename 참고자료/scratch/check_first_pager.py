import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
page = Fetcher.get(url)

for a in page.css('ul.pagination a'):
    print(a.attrib.get('title', ''), a.text.strip(), "->", a.attrib.get('href'))
