import requests
from bs4 import BeautifulSoup

headers = {
    "Upgrade-Insecure-Requests": "1",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
    "sec-ch-ua": '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
    "sec-ch-ua-mobile": "?0",
    "sec-ch-ua-platform": '"Windows"',
}


class Qichezhijia:
    def run(self, url):
        response = requests.get(url, headers=headers, timeout=60)
        response.raise_for_status()

        # 2. 处理内容编码
        response.encoding = response.apparent_encoding or 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        article = soup.findAll('div', class_='tw-w-[750px]')[0]
        title_div = article.findNext('div', {"class": "tw-text-[32px] tw-font-[600] tw-leading-[46px] tw-tracking-normal tw-text-[#111E36]"})
        title = title_div.text

        content = article.findNext("div", {"id": "parent-container"})
        imgs = content.findAll('img')
        img_urls = []
        for img in imgs:
            if img.get('data-src'):
                img_urls.append(img.get('data-src'))

        text = content.text
        return title, img_urls, text
