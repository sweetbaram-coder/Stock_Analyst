from scrapling.fetchers import FetcherSession

with FetcherSession(impersonate="chrome") as s:
    r1 = s.get("https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm")
    print("P1 first title:", r1.css('h4.titles a')[0].text.strip())
    first_d = r1.css('span.byline em:last-of-type')[0].text.strip()
    last_d = r1.css('span.byline em:last-of-type')[-1].text.strip()
    print(f"P 1: [{first_d} ~ {last_d}]")
    
    total = "185125"
    
    for p in range(2, 40):
        url = f"https://news.einfomax.co.kr/news/articleList.html?page={p}&total={total}&box_idxno=&sc_section_code=S1N16&view_type=sm"
        resp = s.get(url)
        items = resp.css('ul.type2 > li')
        if not items:
            print(f"P{p}: No items")
            break
        
        fd = items[0].css('span.byline em:last-of-type')[0].text.strip()
        ld = items[-1].css('span.byline em:last-of-type')[0].text.strip()
        print(f"P{p:2d}: [{fd} ~ {ld}] (items: {len(items)})")
        
        # Stop condition: older than 2026.08.31 (i.e. 2026.08.30 or earlier)
        # 5 days ago from 2026.09.04 is 2026.08.31 (or 2026.08.30)
        if ld < "2026.08.31":
            print(f"==> Reached 5 days limit at Page {p} ({ld})")
            break
