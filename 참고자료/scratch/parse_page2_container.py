from scrapling.parser import Adaptor

with open('scratch/page2.html', 'r', encoding='utf-8') as f:
    html = f.read()

page = Adaptor(html)
links = page.css('a[href*="articleView"]')
print(f"Total articleView links: {len(links)}")
if links:
    first = links[0]
    p = first.parent
    print("Link parent:", p.tag, p.attrib)
    print("Link parent parent:", p.parent.tag, p.parent.attrib)
    if p.parent.parent:
        print("Link grandparent parent:", p.parent.parent.tag, p.parent.parent.attrib)
        if p.parent.parent.parent:
            print("Great-grandparent:", p.parent.parent.parent.tag, p.parent.parent.parent.attrib)

# Let's see all ul classes in page2
for ul in page.css('ul'):
    cls = ul.attrib.get('class', '')
    if 'type' in cls or 'list' in cls or 'article' in cls:
        print("Matching ul:", cls)
