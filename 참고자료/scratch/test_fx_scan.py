import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
import re

total = '185120'
exchange_keywords = ['환율', '달러', '엔화', '위안', '외환', 'FX', 'NDF', '환시', '통화', '원화', '유로', '원/달러', '달러-원', '달러/원']

for p in range(1, 15):
    if p == 1:
        url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
    else:
        url = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total={total}&box_idxno=&sc_section_code=S1N16&view_type=sm"
    
    page = Fetcher.get(url)
    items = page.css('ul.type2 > li')
    if not items:
        print(f"Page {p}: No items")
        break
    
    # Check total from pager if available
    pager_link = page.css('ul.pagination a[href*="total="]')
    if pager_link:
        m = re.search(r'total=(\d+)', pager_link[0].attrib.get('href', ''))
        if m:
            total = m.group(1)
            
    dates = []
    fx_count = 0
    for item in items:
        title_el = item.css('h4.titles a')
        title = title_el[0].text.strip() if title_el else ''
        lead_el = item.css('p.lead a')
        lead = lead_el[0].text.strip() if lead_el else ''
        date_el = item.css('span.byline em:last-of-type')
        dt = date_el[0].text.strip() if date_el else ''
        dates.append(dt)
        
        # Check if FX related
        text_to_check = f"{title} {lead}"
        if any(kw in text_to_check for kw in exchange_keywords):
            fx_count += 1
            
    print(f"Page {p} (items: {len(items)}): Date range [{dates[0]} ~ {dates[-1]}] | FX articles: {fx_count}/{len(items)}")
