from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate="chrome") as s:
    # 1. Visit page 1 to establish session and cookies
    r1 = s.get("https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm")
    print("Page 1 cookies:", dict(s.cookies) if hasattr(s, 'cookies') else "no cookies attr")
    
    # 2. Visit page 2
    r2 = s.get("https://news.einfomax.co.kr/news/articleList.html?page=2&total=185125&box_idxno=&sc_section_code=S1N16&view_type=sm")
    print("Page 2 title:", r2.css('title::text')[0].text.strip() if r2.css('title::text') else '')
    
    # 3. Visit page 3
    r3 = s.get("https://news.einfomax.co.kr/news/articleList.html?page=3&total=185125&box_idxno=&sc_section_code=S1N16&view_type=sm")
    print("Page 3 title:", r3.css('title::text')[0].text.strip() if r3.css('title::text') else '')
    print("Page 3 first title:", r3.css('h4.titles a')[0].text.strip() if r3.css('h4.titles a') else 'None')
