import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher
import re

# 1. Get current page 1
p1_url = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
p1 = Fetcher.get(p1_url)
# Extract total
pager = p1.css('ul.pagination a[href*="total="]')
total_val = None
if pager:
    m = re.search(r'total=(\d+)', pager[0].attrib.get('href', ''))
    if m:
        total_val = m.group(1)

print(f"Current dynamic total from p1: {total_val}")

for p in range(1, 15):
    if p == 1:
        u = p1_url
    else:
        u = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total={total_val}&box_idxno=&sc_section_code=S1N16&view_type=sm"
    
    resp = Fetcher.get(u)
    t = resp.css('title::text')[0].text.strip() if resp.css('title::text') else ''
    c2 = len(resp.css('ul.type2 > li'))
    c1 = len(resp.css('ul.type1 > li'))
    date_str = ""
    if c2 > 0:
        d = resp.css('ul.type2 > li span.byline em:last-of-type')
        date_str = f"[{d[0].text.strip()} ~ {d[-1].text.strip()}]" if d else ""
    print(f"Page {p}: title='{t}' | c2={c2} | c1={c1} | dates={date_str}")
