import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

# Test 1: Direct search parameter on einfomax
url_search = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm&sc_word=%ED%99%98%EC%9C%A8'
page_search = Fetcher.get(url_search)
items_search = page_search.css('ul.type2 > li')
print(f"Search with sc_word=환율 items: {len(items_search)}")
if items_search:
    title_el = items_search[0].css('h4.titles a')
    print("Search result 1 title:", title_el[0].text.strip() if title_el else '')

# Test 2: Standard listing without sc_word
url_std = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm'
page_std = Fetcher.get(url_std)
items_std = page_std.css('ul.type2 > li')
print(f"Standard listing items: {len(items_std)}")
