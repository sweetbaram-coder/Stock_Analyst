from scrapling.parser import Adaptor

p3 = Adaptor(open('scratch/p3_debug.html', 'r', encoding='utf-8').read())
items = p3.css('ul.type1 > li')
print(f"p3 items count: {len(items)}")
for idx, it in enumerate(items[:5], 1):
    t = it.css('h4.titles a')
    title = t[0].text.strip() if t else ''
    byline = [b.text.strip() for b in it.css('.byline em, em') if b.text.strip()]
    print(f"[{idx}] {title} | {byline}")
