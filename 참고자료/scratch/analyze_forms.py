from scrapling.parser import Adaptor

with open('scratch/page1.html', 'r', encoding='utf-8') as f:
    html = f.read()

page = Adaptor(html)

print("=== ALL PAGER LINKS IN PAGE 1 ===")
for idx, a in enumerate(page.css('ul.pagination a')):
    print(f"[{idx}] text='{a.text.strip()}' href='{a.attrib.get('href')}' onclick='{a.attrib.get('onclick')}'")

# Check if there is a form around pagination or list
forms = page.css('form')
print(f"\n=== FORMS ({len(forms)}) ===")
for f in forms:
    print(f"form name='{f.attrib.get('name')}' id='{f.attrib.get('id')}' action='{f.attrib.get('action')}' method='{f.attrib.get('method')}'")
    for inp in f.css('input'):
        print(f"  input name='{inp.attrib.get('name')}' value='{inp.attrib.get('value')}' type='{inp.attrib.get('type')}'")
