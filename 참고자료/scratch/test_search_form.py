import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
import urllib.parse

# Test 1: Search within section
kw = urllib.parse.quote("환율")
u1 = f"https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&sc_area=A&view_type=sm&sc_word={kw}"
p1 = Fetcher.get(u1)
items1 = p1.css('ul.type2 > li, ul.type1 > li')
print(f"Search in section: count={len(items1)}")
if items1:
    print("Item 1 title:", items1[0].css('h4.titles a')[0].text.strip())
    print("Item 1 date:", items1[0].css('span.byline em:last-of-type')[0].text.strip())

# Test 2: General search with sc_area=A
u2 = f"https://news.einfomax.co.kr/news/articleList.html?sc_area=A&view_type=sm&sc_word={kw}"
p2 = Fetcher.get(u2)
items2 = p2.css('ul.type2 > li, ul.type1 > li')
print(f"General search: count={len(items2)}")
if items2:
    print("Item 1 title:", items2[0].css('h4.titles a')[0].text.strip())
    print("Item 1 date:", items2[0].css('span.byline em:last-of-type')[0].text.strip())
