import sys
sys.path.append('scripts')
from scrapling.fetchers import FetcherSession

with FetcherSession() as session:
    # 1. First visit page 1
    p1 = session.get("https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm")
    print("Page 1 status:", p1.status)
    
    # 2. Extract next page links from pagination
    for p in range(2, 10):
        # find link in pagination
        # Or construct with exact parameters
        url = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
        resp = session.get(url)
        t = resp.css('title::text')[0].text.strip() if resp.css('title::text') else ''
        c2 = len(resp.css('ul.type2 > li'))
        c1 = len(resp.css('ul.type1 > li'))
        print(f"Page {p}: title='{t}' | c2={c2} | c1={c1}")
        
        # Check actual links in pager of current page
        pager_links = resp.css('ul.pagination a')
        next_urls = [a.attrib.get('href') for a in pager_links if a.text.strip() == str(p+1)]
        if next_urls:
            print(f"  -> Found exact pager link for next page {p+1}: {next_urls[0]}")
