import os
import re
import traceback
import uuid

import requests

from astra.settings import IMG_PATH
from news.models import NewsDetails, NewsMedia

headers = {
    'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
    'X-XSRF-TOKEN': '83dd90',
    'sec-ch-ua-mobile': '?0',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'application/json, text/plain, */*',
    'MWeibo-Pwa': '1',
    'Referer': 'https://m.weibo.cn/search?containerid=100103type%3D1%26q%3D%23%E8%94%A1%E5%BE%90%E5%9D%A4%23',
    'X-Requested-With': 'XMLHttpRequest',
    'sec-ch-ua-platform': '"Windows"'
}


class WeiboCollector:

    def collect(self, url, news_id):
        response = requests.get(url, headers=headers)

        # 检查响应状态码
        if response.status_code == 200:
            # 使用Beautiful Soup解析页面内容
            result = response.json()
            cards = result.get('data', {}).get('cards')
            for card in cards:
                try:
                    if card.get('card_type') != 9:
                        continue
                    text = card.get('mblog', {}).get('text')
                    msg_info = re.sub(r'<[^>]+>', '', text)
                    if NewsDetails.objects.filter(news_id=news_id):
                        NewsDetails.objects.filter(news_id=news_id).update(msg=msg_info)
                    else:
                        NewsDetails(news_id=news_id, msg=msg_info).save()

                    imgs = card.get('mblog', {}).get('pics')
                    if not imgs:
                        continue
                    for img in imgs:
                        img_url = img.get('url')
                        news_medias = NewsMedia.objects.filter(href=img_url)
                        need_download = True
                        if news_medias:
                            media = news_medias[0].media
                            if os.path.exists(os.path.join(IMG_PATH, media)):
                                NewsMedia(news_id=news_id, media_type='IMG', href=img_url, media=news_medias[0].media).save()
                                need_download = False
                        if need_download:
                            response = requests.get(img_url, headers=headers)
                            if response.status_code == 200:
                                img_id = str(uuid.uuid4())
                                filename = f"{img_id}.jpg"
                                file_path = os.path.join(IMG_PATH, filename)
                                with open(file_path, 'wb') as f:
                                    f.write(response.content)
                                NewsMedia(news_id=news_id, media_type='IMG', href=img_url, media=filename).save()
                        break
                    break
                except Exception:
                    print(traceback.format_exc())
                    continue
