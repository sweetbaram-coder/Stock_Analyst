from scrapling.parser import Adaptor

with open('scratch/page2.html', 'r', encoding='utf-8') as f:
    html = f.read()

page = Adaptor(html)
items = page.css('ul.type1 > li, ul.type2 > li')
print(f"Total items: {len(items)}")

for idx, item in enumerate(items[:5], 1):
    title_el = item.css('h4.titles a')
    title = title_el[0].text.strip() if title_el else ''
    date_el = item.css('.byline em, span.dated, em')
    dates = [d.text.strip() for d in date_el if d.text.strip()]
    print(f"[{idx}] {title} | {dates}")
