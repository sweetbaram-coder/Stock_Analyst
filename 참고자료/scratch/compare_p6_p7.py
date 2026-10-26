import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

url7 = "https://news.einfomax.co.kr/news/articleList.html?page=7&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
p7 = Fetcher.get(url7)
with open('scratch/page7.html', 'w', encoding='utf-8') as f:
    f.write(p7.html_content)

# Look at navigation, breadcrumb, active menu in P7 vs P6
from scrapling.parser import Adaptor
a6 = Adaptor(open('scratch/page6.html', 'r', encoding='utf-8').read())
a7 = Adaptor(open('scratch/page7.html', 'r', encoding='utf-8').read())

print("P6 active menus:", [m.text.strip() for m in a6.css('.active, .current, .selected')])
print("P7 active menus:", [m.text.strip() for m in a7.css('.active, .current, .selected')])
print("P6 head-search or hidden inputs:")
for inp in a6.css('input[type="hidden"]'):
    print(" ", inp.attrib.get('name'), "=", inp.attrib.get('value'))
print("P7 head-search or hidden inputs:")
for inp in a7.css('input[type="hidden"]'):
    print(" ", inp.attrib.get('name'), "=", inp.attrib.get('value'))
