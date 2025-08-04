import base64
import logging
import uuid
from io import BytesIO

import imagehash as imagehash
import requests
from PIL import Image as PILImage
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from asset.models import AssetInfo
from astra.settings import IMG_PATH
from common.response import ok_response, error_response
from image.models import Image

IMAGE_NAMESPACE = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')

logger = logging.getLogger("image")


def download_image(image_url, user_id):
    """下载图片"""
    try:
        response = requests.get(image_url, timeout=30)
        if response.status_code == 200:
            print(f"HTTP status code: {response.status_code}")
            image_bytes = response.content
            a_hash = calculate_ahash(image_bytes)
            img_id = uuid.uuid3(IMAGE_NAMESPACE, a_hash)
            filename = f"{img_id}.png"
            try:
                Image.objects.get(id=img_id)
                logger.info(f"图片{img_id}已存在")
                return img_id
            except Image.DoesNotExist:
                imagedata = response.json().get('data').split(',')[1]
                with open(filename, 'wb') as f:
                    f.write(base64.b64decode(imagedata))
                try:
                    pil_image = PILImage.open(filename)
                    width, height = pil_image.size
                    image_format = pil_image.format
                    image_mode = pil_image.mode
                    spec = {
                        'format': image_format,
                        'mode': image_mode
                    }
                    Image.objects.create(
                        id=img_id,
                        img_name=f"{img_id}.png",
                        img_path=IMG_PATH,
                        width=width,
                        height=height,
                        origin="网络下载",
                        category="normal",
                        creator=user_id,
                        spec=spec
                    )
                    pil_image.verify()
                    pil_image.close()
                    return img_id
                except Exception:
                    logger.error(f"图片{img_id}无法正常打开")
                    raise
    except Exception as e:
        logger.error(f"下载图片失败: {e}")
        raise e


def calculate_ahash(image_bytes):
    """计算图片的aHash值"""
    try:
        image = PILImage.open(BytesIO(image_bytes))
        return str(imagehash.average_hash(image))
    except Exception as e:
        logger.error(f"计算哈希失败: {str(e)}")
        raise


class ImageSearchView(APIView):
    """图片搜索接口"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="通过关键词搜索图片",
        manual_parameters=[
            openapi.Parameter('key', openapi.IN_QUERY, description="图片搜索关键字", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="查询成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER),
                                'urls': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_STRING)
                                )
                            }
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        """搜索图片"""
        key = self.request.query_params.get('key')
        url = "https://googleimg.closeai.store/search?key={}".format(key)
        response = requests.get(url)
        data = response.json()
        img_urls = []
        download_url = "https://googleimg.closeai.store/download?url={}"
        for item in data:
            img_urls.append({
                "url": download_url.format(base64.b64encode(item.encode('utf-8')).decode('utf-8')),
            })

        return ok_response({
            "count": len(img_urls),
            "urls": img_urls
        })


class ImageAddressView(APIView):
    """图片搜索接口"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="通过关键词搜索图片",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='图片url路径'
                )
            },
            required=['url']
        ),
        responses={
            200: openapi.Response(
                description="查询成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'url': openapi.Schema(type=openapi.TYPE_STRING),
                                'data': openapi.Schema(type=openapi.TYPE_STRING)
                            }
                        )
                    }
                )
            )
        }
    )
    def post(self, request):
        """搜索图片"""
        url = request.data.get('url')
        response = requests.get(url)
        if response.status_code == 200:
            image_data = response.json().get('data').split(',')[1]
            source_url = response.json().get('source_url')
            return ok_response({
                'url': source_url,
                "data": image_data
            })
        else:
            return error_response("查找图片路径出错")


class SaveImageView(APIView):
    """保存图片到本地接口"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="将网络图片保存到本地并创建Image记录",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'image_url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='图片路径'
                )
            },
            required=['image_url']
        ),
        responses={
            200: openapi.Response(
                description="保存成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request):
        """保存图片到本地"""

        image_url = request.data.get('image_url')

        try:
            # 下载图片
            download_image(image_url, request.user.id)

            return ok_response("图片保存成功")

        except Exception as e:
            return error_response(f"保存失败: {str(e)}")


class AddToAssetView(APIView):
    """添加到素材集接口"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="将网络图片保存到本地并加入素材集",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'image_url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='图片路径'
                ),
                'asset_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='素材集id'
                )
            },
            required=['image_url', 'asset_id']
        ),
        responses={
            200: openapi.Response(
                description="保存成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER),
                        'message': openapi.Schema(type=openapi.TYPE_STRING),
                        'data': openapi.Schema(type=openapi.TYPE_STRING)
                    }
                )
            )
        }
    )
    def post(self, request):
        """添加图片到素材集"""
        image_url = request.data.get('image_url')
        asset_id = request.data.get('asset_id')
        try:
            # 下载图片

            img_id = download_image(image_url, request.user.id)

            AssetInfo.objects.create(
                set_id=asset_id,
                resource_id=img_id,
                asset_type='image'

            )

            return ok_response("加入素材集成功")

        except Exception as e:
            return error_response(f"保存失败: {str(e)}")
