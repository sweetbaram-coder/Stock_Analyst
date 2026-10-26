from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm")
    page.wait_for_load_state("networkidle")
    
    current_page = 1
    while True:
        items = page.locator("ul.type2 > li")
        count = items.count()
        if count == 0:
            print(f"Page {current_page}: No items")
            break
            
        first_title = items.first.locator("h4.titles a").inner_text()
        first_date = items.first.locator("span.byline em").all_inner_texts()[-1]
        last_title = items.last.locator("h4.titles a").inner_text()
        last_date = items.last.locator("span.byline em").all_inner_texts()[-1]
        
        print(f"Page {current_page:2d}: [{first_date} ~ {last_date}] (count={count}) | {first_title[:20]}")
        
        if last_date < "2026.08.31":
            print(f"==> Reached 5 days limit at Page {current_page} ({last_date})")
            break
            
        current_page += 1
        # Click next page
        # Check if next numeric page exists
        next_btn = page.locator(f"ul.pagination a:text-is('{current_page}')")
        if next_btn.count() > 0:
            next_btn.first.click()
            page.wait_for_load_state("networkidle")
        else:
            # Check for pagination-next or onenext
            one_next = page.locator("li.pagination-onenext a")
            if one_next.count() > 0:
                one_next.first.click()
                page.wait_for_load_state("networkidle")
            else:
                print(f"No next button found at page {current_page}")
                break
                
    browser.close()
