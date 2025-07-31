import requests
from bs4 import BeautifulSoup

headers = {
    "authority": "m.hupu.com",
    "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "accept-language": "zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7",
    "referer": "https://m.hupu.com/score-home",
    "sec-ch-ua": '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
    "sec-fetch-dest": "iframe",
    "sec-fetch-mode": "navigate",
    "sec-fetch-site": "same-origin",
    "sec-fetch-user": "?1",
    "upgrade-insecure-requests": "1",
    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}


class Hupu:
    def run(self, url):
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        # 2. 处理内容编码
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.findAll('div', {"class": "index_bbs-post-web-main__D_K6v"})[0]
        title_div = article.findNext('h1')
        title = title_div.text

        content = article.findNext('div', {"class": "thread-content-detail"})

        imgs = content.findAll('img')
        img_urls = []
        for img in imgs:
            if img.get('src'):
                img_urls.append(img.get('src'))

        text = content.text
        return title, img_urls, text
