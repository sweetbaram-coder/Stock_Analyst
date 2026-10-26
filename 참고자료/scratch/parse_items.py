import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url = 'https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm'
page = Fetcher.get(url)

items = page.css('ul.type2 > li')
print(f"Total items found in ul.type2: {len(items)}")

for idx, item in enumerate(items[:3], 1):
    print(f"\n--- Item {idx} ---")
    title_el = item.css('h4.titles a')
    title = title_el[0].text.strip() if title_el else ''
    href = title_el[0].attrib.get('href', '') if title_el else ''
    
    # Check other text inside view-cont
    view_cont = item.css('.view-cont')
    
    # Try finding summary, date, author
    lead_el = item.css('.lead, p, .summary')
    lead = [p.text.strip() for p in lead_el if p.text.strip()]
    
    byline_el = item.css('.byline, .info, .dated, span, em')
    byline = [b.text.strip() for b in byline_el if b.text.strip()]
    
    print(f"Title: {title}")
    print(f"Link: {href}")
    print(f"Paragraphs/Lead: {lead}")
    print(f"Byline/Spans: {byline}")
    print(f"Item full text: {item.text.strip().split()[:20]}")
