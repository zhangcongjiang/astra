import logging
import os
import time
import uuid

import requests
from bs4 import BeautifulSoup

from astra.settings import IMG_PATH
from image.models import Image
from news.models import NewsMedia, NewsDetails
from PIL import Image as PILImage

headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7',
    'cookie': 'BIDUPSID=F5CE423A66BC1D8E133182B4892AEE71; PSTM=1722415322; BAIDUID=F5CE423A66BC1D8EA87BB15202C4A1D8:FG=1; BD_HOME=1; BD_UPN=12314753; BAIDUID_BFESS=F5CE423A66BC1D8EA87BB15202C4A1D8:FG=1; BA_HECTOR=a0a501218ka1ahaga5850h253fucju1jaju6r1v; ZFY=RSIynL92Y6gyfqoSSW2iDbp6TzO7yM5oTD0wC2h58Es:C; BD_CK_SAM=1; PSINO=3; H_PS_PSSID=60492_60502_60477_60522_60550_60564; delPer=0; BDORZ=B490B5EBF6F3CD402E515D22BCDA1598; baikeVisitId=c7f545cf-9b8a-44a1-a9bd-074b558dc34a; H_PS_645EC=9f79d8YXq53%2FT7ovt7ieD%2F1mpbVNaKF964m3lSZ%2BIfXFCD8PebLsRPt5SmU',
    'origin': 'https://baidu.com',
    'priority': 'u=1, i',
    'referer': 'https://baidu.com/',
    'sec-ch-ua': '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-site',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36',
}

logger = logging.getLogger("news")


class BaiduCollector:

    def collect(self, url, news_id):

        response = requests.get(url, headers=headers)

        # 检查响应状态码
        if response.status_code == 200:
            # 使用Beautiful Soup解析页面内容
            soup = BeautifulSoup(response.text, 'html.parser')

            msg_div = soup.find('div', class_='_no-spacing_4sbbx_4')

            if msg_div:
                msg_info = msg_div.getText().replace('详情', '').replace(" ", "").replace('', '')
            else:
                msg_info = ''
            img_url = soup.find('img', class_='_img_bo7t2_11').get('src')
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
                        filename = f"{img_id}.png"
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

            if NewsDetails.objects.filter(news_id=news_id):
                NewsDetails.objects.filter(news_id=news_id).update(msg=msg_info)
            else:
                NewsDetails(news_id=news_id, msg=msg_info).save()


        else:
            logger.error(f'Failed to retrieve the webpage. Status code:{response.status_code}')
