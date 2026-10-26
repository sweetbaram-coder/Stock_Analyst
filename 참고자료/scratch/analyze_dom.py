import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
import json

url = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm'
page = Fetcher.get(url)

# Print HTML around article list
# Let's find candidate containers
candidates = [
    'section.article-list-content',
    '.article-list',
    '#article-list',
    '.list-block',
    '.item-list',
    '.list-type-1',
    '.table-list',
    'ul.type2',
    '.art_list',
    'section',
    'div[class*="list"]',
    'div[class*="article"]'
]

print("=== CANDIDATE SELECTORS ===")
for c in candidates:
    matches = page.css(c)
    if matches:
        classes = [m.attrib.get('class', '') for m in matches[:5]]
        ids = [m.attrib.get('id', '') for m in matches[:5]]
        print(f"Selector '{c}': {len(matches)} matches (classes: {classes}, ids: {ids})")

# Let's inspect the first article link parent hierarchy
first_link = page.css('a[href*="articleView"]')[1] # index 1 is usually title link
parent = first_link.parent
print("Link parent tag/class:", parent.tag, parent.attrib)
if parent.parent:
    print("Link grandparent tag/class:", parent.parent.tag, parent.parent.attrib)
    if parent.parent.parent:
        print("Link great-grandparent:", parent.parent.parent.tag, parent.parent.parent.attrib)

# Let's check pagination elements
print("\n=== PAGINATION ===")
pager = page.css('.pagination, .paging, .page-nav, a[href*="page="], a[href*="sc_page="]')
print("Pager matches:", len(pager))
for p in pager[:10]:
    print("Pager item:", p.tag, p.attrib, p.text.strip())
