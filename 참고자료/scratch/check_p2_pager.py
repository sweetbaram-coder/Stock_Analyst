from scrapling.fetchers import Fetcher

u2 = "https://news.einfomax.co.kr/news/articleList.html?page=2&total=185125&box_idxno=&sc_section_code=S1N16&view_type=sm"
p2 = Fetcher.get(u2)

print("Page 2 pager links:")
for a in p2.css('ul.pagination a'):
    print(f"text='{a.text.strip()}' title='{a.attrib.get('title')}' href='{a.attrib.get('href')}'")
