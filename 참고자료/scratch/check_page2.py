import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url = 'https://news.einfomax.co.kr/news/articleList.html?page=2&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm'
page = Fetcher.get(url)
print("Status:", page.status)
print("Length:", len(page.html_content))
with open('scratch/page2.html', 'w', encoding='utf-8') as f:
    f.write(page.html_content)

print("Title:", page.css('title::text'))
print("ul.type2:", len(page.css('ul.type2')))
print("li in ul:", len(page.css('ul li')))
print("links to articleView:", len(page.css('a[href*="articleView"]')))
