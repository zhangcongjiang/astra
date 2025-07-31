import requests
from bs4 import BeautifulSoup

headers = {
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
    "cache-control": "max-age=0",
    "if-modified-since": "Thu, 31 Jul 2025 15:35:58 +0800",
    "priority": "u=0, i",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "document",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36"
}


class Gongzhonghao:
    def run(self, url):
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        # 2. 处理内容编码
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.findAll('div', {"id": "img-content"})[0]
        title_div = article.findNext('h1')
        title = title_div.text

        imgs = article.findAll('img')
        img_urls = []
        for img in imgs:
            if img.get('data-src'):
                img_urls.append(img.get('data-src'))

        text = article.findNext('div', {"id": "js_content"}).text
        return title, img_urls, text
