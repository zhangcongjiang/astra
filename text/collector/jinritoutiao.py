import requests

from bs4 import BeautifulSoup

headers = {
    'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'accept-language': 'zh-CN,zh;q=0.9',
    'cookie': 'ttwid=1%7C4RrHpfVtl7LYUvgAhFBdqEvgSsRLBaU6B9lwsSZ3rr8%7C1723173248%7Ca93bf64dc300a1040c2635a587704150f9534d1350337335e74a8c2be2e11e9b',
    'priority': 'u=0, i',
    'referer': 'https://www.toutiao.com/trending/7400690451155652147/?category_name=topic_innerflow&event_type=hot_board&log_pb=%7B%22category_name%22%3A%22topic_innerflow%22%2C%22cluster_type%22%3A%221%22%2C%22enter_from%22%3A%22click_category%22%2C%22entrance_hotspot%22%3A%22outside%22%2C%22event_type%22%3A%22hot_board%22%2C%22hot_board_cluster_id%22%3A%227400690451155652147%22%2C%22hot_board_impr_id%22%3A%222024080911050152D7FD62D9DE5299FF7E%22%2C%22jump_page%22%3A%22hot_board_page%22%2C%22location%22%3A%22news_hot_card%22%2C%22page_location%22%3A%22hot_board_page%22%2C%22rank%22%3A%2221%22%2C%22source%22%3A%22trending_tab%22%2C%22style_id%22%3A%2240132%22%2C%22title%22%3A%22%E6%8B%9C%E7%99%BB%E9%80%80%E9%80%89%E5%90%8E%E2%80%9C%E9%9A%90%E8%BA%AB%E2%80%9D%E4%B8%A4%E5%91%A8%22%7D&rank=21&style_id=40132&topic_id=7400690451155652147',
    'sec-ch-ua': '"Not)A;Brand";v="99", "Google Chrome";v="127", "Chromium";v="127"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'document',
    'sec-fetch-mode': 'navigate',
    'sec-fetch-site': 'same-origin',
    'upgrade-insecure-requests': '1',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36'
}

url = "https://www.toutiao.com/article/7532465744039166498/?log_from=b4ed58b3413c4_1753928867514"


class ToutiaoSpider:

    def run(self, url):
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        # 2. 处理内容编码
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.findAll('div', class_='article-content')[0]
        title_div = article.findNext('h1')
        title = title_div.text

        imgs = article.findAll('img')
        img_urls = []
        for img in imgs:
            if img.get('data-src'):
                img_urls.append(img.get('data-src'))


        text = title_div.findNext('article').text
        return title, img_urls, text
