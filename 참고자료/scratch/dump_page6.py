import sys
sys.path.append('scripts')
from scrapling.fetchers import Fetcher

u6 = "https://news.einfomax.co.kr/news/articleList.html?page=6&total=185120&box_idxno=&sc_section_code=S1N16&view_type=sm"
p6 = Fetcher.get(u6)
with open('scratch/page6.html', 'w', encoding='utf-8') as f:
    f.write(p6.html_content)

pager = p6.css('ul.pagination')
if pager:
    with open('scratch/page6_pager.html', 'w', encoding='utf-8') as f:
        f.write(pager[0].html_content if hasattr(pager[0], 'html_content') else str(pager[0]))
    print("Dumped page 6 pager")
else:
    print("Page 6 has no pagination?")
