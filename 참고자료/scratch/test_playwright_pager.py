from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto("https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&view_type=sm")
    page.wait_for_load_state("networkidle")
    
    print("Initial URL:", page.url)
    print("Initial Title:", page.title())
    first_title = page.locator("h4.titles a").first.inner_text()
    print("First article:", first_title)
    
    # Click page 2
    print("\nClicking Page 2...")
    page.locator("ul.pagination a:has-text('2')").click()
    page.wait_for_load_state("networkidle")
    print("After click 2, URL:", page.url)
    print("After click 2, Title:", page.title())
    first_title_2 = page.locator("h4.titles a").first.inner_text()
    print("Page 2 First article:", first_title_2)
    
    # Click page 3
    print("\nClicking Page 3...")
    page.locator("ul.pagination a:has-text('3')").click()
    page.wait_for_load_state("networkidle")
    print("After click 3, URL:", page.url)
    print("After click 3, Title:", page.title())
    first_title_3 = page.locator("h4.titles a").first.inner_text()
    print("Page 3 First article:", first_title_3)
    
    browser.close()
