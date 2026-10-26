from scrapling.fetchers import Fetcher
import urllib.parse

kw = urllib.parse.quote("환율")
u1 = f"https://news.einfomax.co.kr/news/articleList.html?sc_section_code=S1N16&sc_area=A&view_type=sm&sc_word={kw}"
p1 = Fetcher.get(u1)
items1 = p1.css('ul.type1 > li, ul.type2 > li')
print(f"Total matching items: {len(items1)}")
for idx, item in enumerate(items1[:5], 1):
    titles = item.css('h4.titles a')
    t = titles[0].text.strip() if titles else ''
    byline = [e.text.strip() for e in item.css('.byline em, em, span')]
    print(f"[{idx}] Title: {t}")
    print(f"     Byline: {byline}")
