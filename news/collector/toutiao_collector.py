import logging
import os
import time
import traceback
import uuid

import requests
from bs4 import BeautifulSoup

from astra.settings import IMG_PATH
from image.models import Image
from news.models import NewsMedia, NewsDetails
from PIL import Image as PILImage

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

logger = logging.getLogger("news")


class ToutiaoCollector:

    def collect(self, url, news_id):
        response = requests.get(url, headers=headers)

        # 检查响应状态码
        if response.status_code == 200:
            # 使用Beautiful Soup解析页面内容
            soup = BeautifulSoup(response.text, 'html.parser')
            try:
                img_url = soup.findAll('img')[0].get('src')

                if img_url:
                    news_medias = NewsMedia.objects.filter(href=img_url)
                    need_download = True
                    if news_medias:
                        media = news_medias[0].media
                        if os.path.exists(os.path.join(IMG_PATH, media)):
                            NewsMedia(news_id=news_id, media_type='IMG', href=img_url, media=news_medias[0].media).save()
                            need_download = False
                    if need_download:
                        try:
                            response = requests.get(img_url, headers=headers)
                            response.raise_for_status()

                            if response.status_code == 200:
                                img_id = str(uuid.uuid4())
                                filename = f"{img_id}.jpg"
                                file_path = os.path.join(IMG_PATH, filename)
                                with open(file_path, 'wb') as f:
                                    f.write(response.content)
                                NewsMedia(news_id=news_id, media_type='IMG', href=img_url, media=filename).save()

                                pil_image = PILImage.open(file_path)
                                width, height = pil_image.size
                                image_format = pil_image.format
                                image_mode = pil_image.mode

                                spec = {
                                    'format': image_format,
                                    'mode': image_mode
                                }

                                Image(
                                    img_name=filename,
                                    category='normal',
                                    img_path=IMG_PATH,
                                    width=int(width),
                                    height=int(height),
                                    origin='热点新闻',
                                    creator=0,
                                    spec=spec
                                ).save()
                                logger.info(f"image {filename} download success!")
                                # 防止反爬机制
                                time.sleep(0.1)

                        except requests.RequestException as e:
                            logger.error(f"Error downloading image {img_url}: {e}")

                else:
                    logger.error("No URL found.")
            except Exception:
                logger.error(traceback.format_exc())
            try:

                msg_div = soup.findAll('a', class_='title')
                if msg_div and len(msg_div):
                    msg = msg_div[0].getText()

                else:
                    msg = '请通过关联链接查看新闻详情'
                news_detail, created = NewsDetails.objects.get_or_create(
                    news_id=news_id,
                    defaults={'msg': msg}
                )
                if not created:
                    news_detail.msg = msg
                    news_detail.save()
            except Exception:
                logger.error(traceback.format_exc())
        else:
            logger.error(f'Failed to retrieve the webpage. Status code:{response.status_code}')
