from scrapling.fetchers import Fetcher

u3 = "https://news.einfomax.co.kr/news/articleList.html?page=3&total=185125&box_idxno=&sc_section_code=S1N16&view_type=sm"
p3 = Fetcher.get(u3)
print("p3 status:", p3.status)
print("p3 title:", p3.css('title::text')[0].text.strip() if p3.css('title::text') else '')
print("p3 ul.type2:", len(p3.css('ul.type2 > li')))
print("p3 ul.type1:", len(p3.css('ul.type1 > li')))

with open('scratch/p3_debug.html', 'w', encoding='utf-8') as f:
    f.write(p3.html_content)
