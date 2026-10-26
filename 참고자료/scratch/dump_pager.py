import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm'
page = Fetcher.get(url)

pager = page.css('ul.pagination')
if pager:
    with open('scratch/pager.html', 'w', encoding='utf-8') as f:
        f.write(pager[0].html_content if hasattr(pager[0], 'html_content') else str(pager[0]))
    print("Dumped pagination HTML")
else:
    print("Pagination not found")
