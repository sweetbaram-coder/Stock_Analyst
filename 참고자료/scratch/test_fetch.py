import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
from utils import detect_softblock

url = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm'
page = Fetcher.get(url)
print('Status:', page.status)
print('Length:', len(page.html_content))
print('Title:', page.css('title::text'))

# Check softblock
softblock = detect_softblock(page.html_content, status=page.status)
print('Softblock:', softblock)

# Sample elements
links = page.css('a[href*="articleView"]')
print('articleView links count:', len(links))
if links:
    print('First 3 links:')
    for a in links[:3]:
        print(' - text:', a.text.strip())
        print('   href:', a.attrib.get('href'))
