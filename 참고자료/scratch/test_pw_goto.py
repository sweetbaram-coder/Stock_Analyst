from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    
    # First visit page 1
    page.goto("https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm")
    page.wait_for_load_state("domcontentloaded")
    
    for p_num in range(1, 26):
        if p_num == 1:
            u = "https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm"
        else:
            u = f"https://news.einfomax.co.kr/news/articleList.html?page={p_num}&total=185125&box_idxno=&sc_section_code=S1N16&view_type=sm"
            page.goto(u)
            page.wait_for_load_state("domcontentloaded")
            
        items = page.locator("ul.type2 > li")
        cnt = items.count()
        if cnt == 0:
            print(f"P{p_num}: No items")
            break
            
        first_d = items.first.locator("span.byline em").all_inner_texts()[-1]
        last_d = items.last.locator("span.byline em").all_inner_texts()[-1]
        print(f"P{p_num:2d}: [{first_d} ~ {last_d}]")
        
        if last_d < "2026.08.31":
            print(f"==> Successfully reached 5 days ago limit (prior to 2026.08.31) at Page {p_num}!")
            break
            
    browser.close()
