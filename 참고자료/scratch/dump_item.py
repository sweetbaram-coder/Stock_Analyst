import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm'
page = Fetcher.get(url)

items = page.css('ul.type2 > li')
first_item = items[0]

with open('scratch/first_item.html', 'w', encoding='utf-8') as f:
    # Get raw html of the first item
    f.write(first_item.html_content if hasattr(first_item, 'html_content') else str(first_item))

print("Dumped first item.")
