import logging
import os
import re
import shutil
import traceback
import uuid
from urllib.parse import urlparse

import markdown
import requests
from PIL import Image as PILImage
from bs4 import BeautifulSoup
from django.http import HttpResponse, Http404
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from asset.models import AssetInfo, Asset
from astra.settings import ARTICLE_PATH, IMG_PATH
from common.response import ok_response, error_response
from common.text_utils import TextUtils
from image.models import Image
from video.models import VideoAsset
from voice.models import Sound
from .collector.gongzhonghao import Gongzhonghao
from .collector.hupu import Hupu
from .collector.jinritoutiao import ToutiaoSpider
from .collector.qichezhijia import Qichezhijia
from .collector.xiaohongshu import Xiaohongshu
from .models import Text, Graph, Dynamic, DynamicImage
from .serializers import TextSerializer, TextDetailSerializer, TextUploadSerializer, DynamicSerializer, DynamicDetailSerializer

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
logger = logging.getLogger("text")

text_utils = TextUtils()


def process_images_in_content(content, image_set_id, user):
    """处理内容中的图片（与TextUploadView中的方法相同）"""
    processed_content = content

    # 匹配markdown格式的图片：![alt](url)
    markdown_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
    # 匹配HTML格式的图片：<img src="url">
    html_pattern = r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*>'

    def replace_image_path(image_url):
        """复制图片并返回新路径"""
        try:
            # 检查图片是否存在
            if image_url.startswith(('http://', 'https://')):
                # 网络图片 - 检查是否可访问
                try:
                    response = requests.head(image_url, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"网络图片不存在或无法访问: {image_url}")
                        return image_url
                except Exception as e:
                    logger.error(f"检查网络图片失败: {str(e)}, URL: {image_url}")
                    return image_url
            else:
                # 本地已存在
                if image_url.startswith(IMG_PATH):
                    logger.info(f"图片已处理：{image_url}")
                    return image_url
                # 本地路径 - 检查文件是否存在
                if not os.path.exists(image_url):
                    logger.error(f"本地图片文件不存在: {image_url}")
                    return image_url

            # 生成新的图片ID
            img_id = str(uuid.uuid4())

            if image_url.startswith(('http://', 'https://')):
                # 网络图片
                response = requests.get(image_url, timeout=10, stream=True)
                if response.status_code == 200:
                    # 获取文件扩展名
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        file_extension = '.jpg'
                    elif 'png' in content_type:
                        file_extension = '.png'
                    elif 'gif' in content_type:
                        file_extension = '.gif'
                    elif 'webp' in content_type:
                        file_extension = '.webp'
                    else:
                        # 尝试从URL获取扩展名
                        parsed_url = urlparse(image_url)
                        file_extension = os.path.splitext(parsed_url.path)[1] or '.jpg'

                    # 保存文件
                    new_filename = f"{img_id}{file_extension}"
                    new_file_path = os.path.join(IMG_PATH, new_filename)

                    with open(new_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            else:
                # 本地路径
                file_extension = os.path.splitext(image_url)[1] or '.jpg'
                new_filename = f"{img_id}{file_extension}"
                new_file_path = os.path.join(IMG_PATH, new_filename)

                shutil.copy2(image_url, new_file_path)
            pil_image = PILImage.open(new_file_path)
            width, height = pil_image.size
            image_format = pil_image.format
            image_mode = pil_image.mode

            spec = {
                'format': image_format,
                'mode': image_mode
            }
            Image(id=img_id, img_name=new_filename, img_path=IMG_PATH, origin="图文关联", creator=user, height=height, width=width, spec=spec).save()
            AssetInfo(resource_id=img_id, set_id=image_set_id, asset_type='image').save()
            return f"/media/images/{new_filename}"

        except Exception as e:
            logger.error(f"处理图片失败: {str(e)}, URL: {image_url}")
            return image_url  # 如果处理失败，返回原路径

    # 处理markdown格式图片
    def replace_markdown_image(match):
        alt_text = match.group(1)
        image_url = match.group(2)
        new_path = replace_image_path(image_url)
        return f'![{alt_text}]({new_path})'

    # 处理HTML格式图片
    def replace_html_image(match):
        full_tag = match.group(0)
        image_url = match.group(1)
        new_path = replace_image_path(image_url)
        return full_tag.replace(image_url, new_path)

    # 替换所有图片路径
    processed_content = re.sub(markdown_pattern, replace_markdown_image, processed_content)
    processed_content = re.sub(html_pattern, replace_html_image, processed_content)

    return processed_content


def process_images_for_dynamic(content, dynamic_id, user_id):
    """处理动态内容中的图片：复制到本地、创建 Image 记录，并在 DynamicImage 里建立关联与顺序，同时返回替换后的内容路径。"""
    processed_content = content

    markdown_pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
    html_pattern = r'<img[^>]+src=["\']([^"\'>]+)["\'][^>]*>'

    # 记录图片顺序
    created_image_ids = []

    def replace_image_path(image_url):
        try:
            # 如果是网络图片，先探测可访问性
            if image_url.startswith(('http://', 'https://')):
                try:
                    response = requests.head(image_url, timeout=10)
                    if response.status_code != 200:
                        logger.error(f"网络图片不可访问: {image_url}")
                        return image_url
                except Exception as e:
                    logger.error(f"检查网络图片失败: {str(e)}, URL: {image_url}")
                    return image_url
            else:
                # 本地路径
                if image_url.startswith(IMG_PATH):
                    logger.info(f"图片已在本地: {image_url}")
                    # 推断文件名与扩展名
                    filename = os.path.basename(image_url)
                    img_id = str(uuid.uuid4())
                    new_file_path = os.path.join(IMG_PATH, filename)
                    # 为保持一致性仍创建 Image 记录
                    try:
                        pil_image = PILImage.open(new_file_path)
                        width, height = pil_image.size
                        image_format = pil_image.format
                        image_mode = pil_image.mode
                        spec = {'format': image_format, 'mode': image_mode}
                        Image(id=img_id, img_name=filename, img_path=IMG_PATH, origin="动态关联", height=height, creator=user_id, width=width,
                              spec=spec).save()
                        created_image_ids.append(img_id)
                        DynamicImage(dynamic_id=str(dynamic_id), image_id=img_id).save()
                        return f"/media/images/{filename}"
                    except Exception:
                        return image_url
                if not os.path.exists(image_url):
                    logger.error(f"本地图片不存在: {image_url}")
                    return image_url

            # 生成新的图片ID
            img_id = str(uuid.uuid4())

            if image_url.startswith(('http://', 'https://')):
                response = requests.get(image_url, timeout=10, stream=True)
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        file_extension = '.jpg'
                    elif 'png' in content_type:
                        file_extension = '.png'
                    elif 'gif' in content_type:
                        file_extension = '.gif'
                    elif 'webp' in content_type:
                        file_extension = '.webp'
                    else:
                        parsed_url = urlparse(image_url)
                        file_extension = os.path.splitext(parsed_url.path)[1] or '.jpg'
                    new_filename = f"{img_id}{file_extension}"
                    new_file_path = os.path.join(IMG_PATH, new_filename)
                    with open(new_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
            else:
                file_extension = os.path.splitext(image_url)[1] or '.jpg'
                new_filename = f"{img_id}{file_extension}"
                new_file_path = os.path.join(IMG_PATH, new_filename)
                shutil.copy2(image_url, new_file_path)

            pil_image = PILImage.open(new_file_path)
            width, height = pil_image.size
            image_format = pil_image.format
            image_mode = pil_image.mode
            spec = {'format': image_format, 'mode': image_mode}
            Image(id=img_id, img_name=new_filename, img_path=IMG_PATH, origin="动态关联", height=height, creator=user_id, width=width,
                  spec=spec).save()
            created_image_ids.append(img_id)
            DynamicImage(dynamic_id=str(dynamic_id), image_id=img_id).save()
            return f"/media/images/{new_filename}"
        except Exception as e:
            logger.error(f"处理图片失败: {str(e)}, URL: {image_url}")
            return image_url

    def replace_markdown_image(match):
        alt_text = match.group(1)
        image_url = match.group(2)
        new_path = replace_image_path(image_url)
        return f'![{alt_text}]({new_path})'

    def replace_html_image(match):
        full_tag = match.group(0)
        image_url = match.group(1)
        new_path = replace_image_path(image_url)
        return full_tag.replace(image_url, new_path)

    processed_content = re.sub(markdown_pattern, replace_markdown_image, processed_content)
    processed_content = re.sub(html_pattern, replace_html_image, processed_content)

    return processed_content


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return ok_response(data={
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class TextListView(generics.ListAPIView):
    """文章列表接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TextSerializer
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description="获取文章列表",
        manual_parameters=[
            openapi.Parameter(
                'title', openapi.IN_QUERY,
                description="文章标题模糊搜索",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'creator', openapi.IN_QUERY,
                description="创建者ID精确搜索",
                type=openapi.TYPE_INTEGER
            ),
            openapi.Parameter(
                'publish', openapi.IN_QUERY,
                description="发布状态筛选 (true/false)",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'origin', openapi.IN_QUERY,
                description="来源",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'start_time', openapi.IN_QUERY,
                description="开始时间 (格式: YYYY-MM-DDTHH:MM:SS)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'end_time', openapi.IN_QUERY,
                description="结束时间 (格式: YYYY-MM-DDTHH:MM:SS，默认今天)",
                type=openapi.TYPE_STRING
            ),
        ],
        responses={
            200: openapi.Response(
                description="文章列表获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": {
                            "count": 1,
                            "next": None,
                            "previous": None,
                            "results": [
                                {
                                    "id": "123e4567-e89b-12d3-a456-426614174000",
                                    "title": "示例文章",
                                    "publish": True,
                                    "creator": "123e4567-e89b-12d3-a456-426614174001",
                                    "create_time": "2024-01-01T12:00:00Z"
                                }
                            ]
                        },
                        "msg": "success"
                    }
                }
            )
        }
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Text.objects.all().order_by('-create_time')

        # 标题模糊搜索
        title = self.request.query_params.get('title')
        if title:
            queryset = queryset.filter(title__icontains=title)

        # 创建者精确搜索
        creator = self.request.query_params.get('creator', self.request.user.id)
        if creator:
            queryset = queryset.filter(creator=creator)

        # 发布状态筛选
        publish = self.request.query_params.get('publish')
        if publish is not None:
            publish_bool = publish.lower() == 'true'
            queryset = queryset.filter(publish=publish_bool)

        origin = self.request.query_params.get('origin')
        if origin:
            queryset = queryset.filter(origin=origin)

        # 时间范围筛选
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')

        if start_time and not end_time:
            end_time = timezone.now().strftime(TIME_FORMAT)

        if start_time:
            try:
                start_datetime = timezone.datetime.strptime(start_time, TIME_FORMAT)
                queryset = queryset.filter(create_time__gte=start_datetime)
            except ValueError:
                pass

        if end_time:
            try:
                end_datetime = timezone.datetime.strptime(end_time, TIME_FORMAT)
                queryset = queryset.filter(create_time__lte=end_datetime)
            except ValueError:
                pass

        return queryset


class TextDetailView(generics.RetrieveAPIView):
    """文章详情接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = TextDetailSerializer
    queryset = Text.objects.all()
    lookup_field = 'id'

    @swagger_auto_schema(
        operation_description="获取指定文章详情",
        responses={
            200: openapi.Response(
                description="文章详情获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "示例文章",
                            "publish": True,
                            "creator": "123e4567-e89b-12d3-a456-426614174001",
                            "create_time": "2024-01-01T12:00:00Z",
                            "content": "# 文章内容\n\n这是文章的markdown内容..."
                        },
                        "msg": "success"
                    }
                }
            ),
            404: openapi.Response(description="文章不存在")
        }
    )
    def get(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return ok_response(data=serializer.data)
        except Text.DoesNotExist:
            return error_response("文章不存在")


class TextDeleteView(APIView):
    """文章删除接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="删除指定文章",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'text_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='文章ID'
                )
            },
            required=['text_id']
        ),
        responses={
            200: openapi.Response(
                description="文章删除成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": None,
                        "msg": "文章删除成功"
                    }
                }
            ),
            404: openapi.Response(description="文章不存在")
        }
    )
    def post(self, request):
        text_id = request.data.get('text_id')

        if not text_id:
            return error_response("请提供文章ID")

        try:
            # 验证UUID格式
            uuid.UUID(text_id)
        except ValueError:
            return error_response("无效的文章ID格式")

        try:
            text = Text.objects.get(id=text_id)

            # 删除文章文件
            file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception as e:
                    return error_response(f"删除文章文件失败: {str(e)}")
            try:

                asset = Asset.objects.get(id=text.id)
                asset_infos = AssetInfo.objects.filter(set_id=asset.id)
                for info in asset_infos:
                    if info.asset_type == 'image':
                        Image.objects.filter(id=info.resource_id).delete()
                    elif info.asset_type == 'sound':
                        Sound.objects.filter(id=info.resource_id).delete()
                    elif info.asset_type == 'text':
                        Graph.objects.filter(id=info.resource_id).delete()
                    elif info.asset_type == 'video':
                        VideoAsset.objects.filter(id=info.resource_id).delete()
                    else:
                        logger.error(f"不支持的类型：{info.asset_type}")
                    info.delete()
                asset.delete()
            except Asset.DoesNotExist:
                logger.error("文案不存在，不用删除")

            # 删除数据库记录
            text.delete()

            return ok_response("文章删除成功")

        except Text.DoesNotExist:
            return error_response("文章不存在")
        except Exception as e:
            return error_response(f"删除文章失败: {str(e)}")


class TextDownloadView(APIView):
    """文章下载接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="下载指定文章的markdown文件",
        responses={
            200: openapi.Response(
                description="文章下载成功",
                content={
                    'application/octet-stream': openapi.Schema(type=openapi.TYPE_FILE)
                }
            ),
            404: openapi.Response(description="文章不存在")
        }
    )
    def get(self, request, text_id):
        try:
            text = Text.objects.get(id=text_id)
            md_file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")
            file_path = os.path.join(ARTICLE_PATH, f"{text_id}.docx")
            if os.path.exists(file_path):
                with open(file_path, 'rb') as f:
                    response = HttpResponse(f, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                    response['Content-Disposition'] = f'attachment; filename="{text.title}.docx"'
                    return response
            else:
                if os.path.exists(md_file_path):
                    text_utils.convert_md_to_doc(md_file_path, file_path)
                    with open(file_path, 'rb') as f:
                        response = HttpResponse(f, content_type='application/vnd.openxmlformats-officedocument.wordprocessingml.document')
                        response['Content-Disposition'] = f'attachment; filename="{text.title}.docx"'
                        return response
                else:

                    return error_response(
                        "源文件不存在"
                    )

        except Exception as e:
            return error_response(
                "下载出错"
            )


class TextUrlImportView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="通过网络URL导入图文内容",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'url': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="网络URL地址"
                ),
                'origin': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="来源"
                ),
            },
            required=['url', 'title']
        ),
        responses={
            201: openapi.Response(
                description="导入成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "导入的文章",
                            "asset_count": {
                                "image_count": 3,
                                "text_count": 5,
                                "total_count": 8
                            }
                        },
                        "msg": "导入成功"
                    }
                }
            ),
            400: openapi.Response(description="请求参数错误")
        }
    )
    def post(self, request):
        origin_map = {
            '今日头条': ToutiaoSpider(),
            '微信公众号': Gongzhonghao(),
            '虎扑': Hupu(),
            '小红书': Xiaohongshu(),
            '汽车之家': Qichezhijia()
        }
        url = request.data.get('url')
        origin = request.data.get('origin')
        user = request.user.id
        if not url:
            return error_response("URL不能为空")
        if not origin:
            return error_response("来源不能为空")

        # 验证URL格式
        if not url.startswith(('http://', 'https://')):
            return error_response("请提供有效的HTTP/HTTPS URL")
        try:

            title, img_urls, text = origin_map.get(origin).run(url)
        except Exception:
            return error_response("URL解析失败")
        text = re.sub(r'\n\s*\n', '\n\n', text).strip()

        # 生成新的文章ID
        text_id = str(uuid.uuid4())
        Asset(id=text_id, set_name=title[:30], creator=user).save()
        file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")
        with open(file_path, 'w', encoding='utf-8') as file:

            for img_url in img_urls:
                img_id = str(uuid.uuid4())
                response = requests.get(img_url, timeout=30, stream=True)
                if response.status_code == 200:
                    # 获取文件扩展名
                    content_type = response.headers.get('content-type', '')
                    if 'jpeg' in content_type or 'jpg' in content_type:
                        file_extension = '.jpg'
                    elif 'png' in content_type:
                        file_extension = '.png'
                    elif 'gif' in content_type:
                        file_extension = '.gif'
                    elif 'webp' in content_type:
                        file_extension = '.webp'
                    else:
                        # 尝试从URL获取扩展名
                        parsed_url = urlparse(img_url)
                        file_extension = os.path.splitext(parsed_url.path)[1] or '.jpg'

                    # 保存文件
                    new_filename = f"{img_id}{file_extension}"
                    new_file_path = os.path.join(IMG_PATH, new_filename)

                    with open(new_file_path, 'wb') as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                    pil_image = PILImage.open(new_file_path)
                    width, height = pil_image.size
                    image_format = pil_image.format
                    image_mode = pil_image.mode

                    spec = {
                        'format': image_format,
                        'mode': image_mode
                    }
                    Image(id=img_id, img_name=new_filename, img_path=IMG_PATH, origin="图文关联", creator=user, height=height, width=width,
                          spec=spec).save()
                    AssetInfo(resource_id=img_id, set_id=text_id, asset_type='image').save()
                    file.write(f'![](/media/images/{new_filename})\n\n')

            for p in text.replace("。", "\n").split('\n'):
                if p.strip():
                    graph_id = str(uuid.uuid4())
                    Graph(id=graph_id, text=p.strip()).save()
                    AssetInfo(set_id=text_id, asset_type='text', resource_id=graph_id).save()
                    file.write(p.strip() + "。\n\n")

            # 选取第一张图片作为封面
            cover = AssetInfo.objects.filter(set_id=text_id, asset_type='image').order_by('index').first()
            cover_id = cover.resource_id if cover else None

            Text.objects.create(
                id=text_id,
                title=title[:30],
                origin=origin,
                publish=False,
                creator=user,
                cover_id=cover_id
            )

            return ok_response(
                "导入成功"
            )


class TextUploadView(APIView):
    """文章上传接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="上传Markdown文章",
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description="Markdown文件(.md格式)"
            ),
            openapi.Parameter(
                'title', openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                required=True,
                description="文章标题"
            )
        ],
        responses={
            201: openapi.Response(
                description="文章上传成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "示例文章",
                            "publish": False,
                            "creator": "123e4567-e89b-12d3-a456-426614174001",
                            "create_time": "2024-01-01T12:00:00Z"
                        },
                        "msg": "文章上传成功"
                    }
                }
            ),
            400: openapi.Response(description="请求参数错误")
        }
    )
    def post(self, request):
        serializer = TextUploadSerializer(data=request.data)

        if not serializer.is_valid():
            return error_response(f"参数验证失败: {serializer.errors}")

        file = serializer.validated_data['file']
        title = serializer.validated_data['title']

        # 验证文件格式
        if not file.name.lower().endswith('.md'):
            return error_response("只支持.md格式的文件")

        # 生成新的文章ID
        text_id = str(uuid.uuid4())

        # 保存文件
        file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")
        try:
            # 读取文件内容
            file_content = ''
            for chunk in file.chunks():
                file_content += chunk.decode('utf-8')

            # 创建Asset
            Asset(id=text_id, set_name=title[:30], creator=str(request.user.id)).save()

            # 处理文件内容中的图片（使用 text_id 作为图片集ID）
            processed_content = process_images_in_content(file_content, text_id, request.user.id)

            # 解析Markdown内容为Graph对象
            try:
                parse_markdown_to_graphs(file_content, text_id)

            except Exception as e:
                logger.error(f"解析Markdown段落失败: {str(e)}")
                # 如果高级解析失败，使用简单解析

            # 保存处理后的内容到文件
            with open(file_path, 'w', encoding='utf-8') as destination:
                destination.write(processed_content)

            # 选取第一张图片作为封面
            cover = AssetInfo.objects.filter(set_id=text_id, asset_type='image').order_by('index').first()
            cover_id = cover.resource_id if cover else None

            # 创建数据库记录（带封面ID）
            text = Text.objects.create(
                id=text_id,
                title=title[:30],
                origin="本地导入",
                publish=False,
                creator=request.user.id,  # 使用当前用户ID作为创建者
                cover_id=cover_id
            )

            return ok_response(
                "上传成功"
            )

        except Exception as e:
            logger.error(traceback.format_exc())
            # 如果数据库操作失败，删除已保存的文件和创建的数据
            if file_path in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    logger.error(traceback.format_exc())

            # 清理可能创建的Asset和AssetInfo
            try:
                Asset.objects.filter(id=text_id).delete()
                AssetInfo.objects.filter(set_id=text_id).delete()
            except Exception:
                logger.error(traceback.format_exc())

            return error_response(f"文章上传失败: {str(e)}")


class TextSaveView(APIView):
    """图文保存接口（支持新建和更新）"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="保存图文（新建或更新）",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'text_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description="文章ID，不提供则为新建操作"
                ),
                'title': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="文章标题"
                ),
                'content': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="文章内容（Markdown格式）"
                )
            },
            required=['title', 'content']
        ),
        responses={
            200: openapi.Response(
                description="保存成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "示例文章",
                            "creator": "123e4567-e89b-12d3-a456-426614174001",
                            "create_time": "2024-01-01T12:00:00Z",
                            "operation": "created"  # 或 "updated"
                        },
                        "msg": "保存成功"
                    }
                }
            ),
            400: openapi.Response(description="请求参数错误"),
            404: openapi.Response(description="文章不存在（更新操作时）")
        }
    )
    def post(self, request):
        text_id = request.data.get('text_id')
        title = request.data.get('title')
        content = request.data.get('content')
        user = request.user.id

        # 处理图片的逻辑已移动到具体的新建/更新方法中，确保使用文章ID作为图片集ID
        # if content:
        #     content = process_images_in_content(content, title, user)

        try:
            if text_id:
                return self._update_text(text_id, title, content, user)
            else:
                return self._create_text(title, content, user)
        except Exception as e:
            return error_response(f"保存失败: {str(e)}")

    def _create_text(self, title, content, user_id):
        """新建文章"""
        # 生成新的文章ID
        text_id = str(uuid.uuid4())
        file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")

        try:
            # 确保目录存在
            os.makedirs(ARTICLE_PATH, exist_ok=True)

            # 先处理图片（使用新生成的 text_id 作为图片集ID）
            processed_content = process_images_in_content(content or "", text_id, user_id)

            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(processed_content)

            # 选取第一张图片作为封面
            cover = AssetInfo.objects.filter(set_id=text_id, asset_type='image').order_by('index').first()
            cover_id = cover.resource_id if cover else None

            # 创建数据库记录（带封面ID）
            Text.objects.create(
                id=text_id,
                title=title,
                origin="用户创建",
                creator=user_id,
                cover_id=cover_id
            )

            return ok_response(
                "创建成功"
            )

        except Exception as e:
            # 如果数据库操作失败，删除已保存的文件
            if os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass
            raise e

    def _update_text(self, text_id, title, content, user_id):
        """更新文章"""
        try:
            # 验证文章是否存在
            text = Text.objects.get(id=text_id)

            file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")

            try:
                # 更新文件内容前处理图片（使用已有的 text_id 作为图片集ID）
                processed_content = process_images_in_content(content or "", text_id, user_id)

                # 更新文件内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(processed_content)

                # 更新数据库记录
                text.title = title
                text.save()

                return ok_response(
                    "保存成功"
                )

            except Exception as e:
                return error_response(f"保存失败：{e}")

        except Text.DoesNotExist:
            return error_response("文章不存在")


def parse_markdown_to_graphs(content, asset_id):
    """解析Markdown内容为Graph对象"""
    # 1. 移除图片标记
    md_str = re.sub(r'!\[[^\]]*\]\(([^\)]+)\)', '', content)
    # 2. 转换Markdown为HTML
    html = markdown.markdown(md_str)

    # 3. 用BeautifulSoup提取纯文本
    soup = BeautifulSoup(html, 'html.parser')
    text = soup.get_text()

    # 4. 清理多余空行
    text = re.sub(r'\n\s*\n', '\n\n', text).strip()
    for p in text.split('\n'):
        if p.strip():
            graph_id = str(uuid.uuid4())
            Graph(id=graph_id, text=p.strip()).save()
            AssetInfo(set_id=asset_id, asset_type='text', resource_id=graph_id).save()

    return [p.strip() for p in text.split('\n') if p.strip()]


class TextCoverReplaceView(APIView):
    """替换图文封面接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="替换指定文章的封面图片（需为文章关联的图片）",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'text_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_UUID,
                    description='文章ID'
                ),
                'cover_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='封面图片ID（Image.id）'
                ),
            },
            required=['text_id', 'cover_id']
        ),
        responses={
            200: openapi.Response(
                description="封面替换成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": None,
                        "msg": "封面替换成功"
                    }
                }
            ),
            400: openapi.Response(description="请求参数错误"),
            404: openapi.Response(description="文章或图片不存在")
        }
    )
    def post(self, request):
        text_id = request.data.get('text_id')
        cover_id = request.data.get('cover_id')

        if not text_id or not cover_id:
            return error_response("缺少必要参数: text_id 或 cover_id")

        # 校验文章存在
        try:
            text = Text.objects.get(id=text_id)
        except Text.DoesNotExist:
            return error_response("文章不存在")

        # 校验图片存在
        from image.models import Image
        if not Image.objects.filter(id=cover_id).exists():
            return error_response("封面图片不存在")

        # 校验图片属于该文章的资源集合
        image_in_set = AssetInfo.objects.filter(
            set_id=text_id,
            asset_type='image',
            resource_id=cover_id
        ).exists()
        if not image_in_set:
            return error_response("封面图片不属于该文章，请先将图片关联到该文章")

        # 更新封面
        text.cover_id = cover_id
        text.save(update_fields=['cover_id'])

        return ok_response("封面替换成功")


class DynamicListView(generics.ListAPIView):
    """动态列表接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DynamicSerializer
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description="获取动态列表",
        manual_parameters=[
            openapi.Parameter('title', openapi.IN_QUERY, description="标题模糊搜索", type=openapi.TYPE_STRING),
            openapi.Parameter('creator', openapi.IN_QUERY, description="创建者ID精确搜索", type=openapi.TYPE_INTEGER),
            openapi.Parameter('publish', openapi.IN_QUERY, description="发布状态筛选 (true/false)", type=openapi.TYPE_BOOLEAN),
            openapi.Parameter('origin', openapi.IN_QUERY, description="来源", type=openapi.TYPE_STRING),
            openapi.Parameter('start_time', openapi.IN_QUERY, description="开始时间 (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_time', openapi.IN_QUERY, description="结束时间 (YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
        ],
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    def get_queryset(self):
        queryset = Dynamic.objects.all().order_by('-create_time')
        title = self.request.query_params.get('title')
        if title:
            queryset = queryset.filter(title__icontains=title)
        creator = self.request.query_params.get('creator', self.request.user.id)
        if creator:
            queryset = queryset.filter(creator=creator)
        publish = self.request.query_params.get('publish')
        if publish is not None:
            publish_bool = str(publish).lower() == 'true'
            queryset = queryset.filter(publish=publish_bool)
        origin = self.request.query_params.get('origin')
        if origin:
            queryset = queryset.filter(origin=origin)
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')
        if start_time and not end_time:
            end_time = timezone.now().strftime(TIME_FORMAT)
        if start_time:
            try:
                start_datetime = timezone.datetime.strptime(start_time, TIME_FORMAT)
                queryset = queryset.filter(create_time__gte=start_datetime)
            except ValueError:
                pass
        if end_time:
            try:
                end_datetime = timezone.datetime.strptime(end_time, TIME_FORMAT)
                queryset = queryset.filter(create_time__lte=end_datetime)
            except ValueError:
                pass
        return queryset


class DynamicDetailView(generics.RetrieveAPIView):
    """动态详情接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = DynamicDetailSerializer
    queryset = Dynamic.objects.all()
    lookup_field = 'id'

    @swagger_auto_schema(operation_description="获取指定动态详情")
    def get(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return ok_response(data=serializer.data)
        except Dynamic.DoesNotExist:
            return error_response("动态不存在")


class DynamicCreateView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="新增动态（multipart/form-data）",
        manual_parameters=[
            openapi.Parameter('title', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description='标题'),
            openapi.Parameter('content', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description='文本内容'),
            openapi.Parameter('images', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True, description='图片文件，支持多文件，使用同名字段传递多个'),
            openapi.Parameter('publish', openapi.IN_FORM, type=openapi.TYPE_BOOLEAN, required=False, description='是否发布'),
        ],
    )
    def post(self, request):
        title = request.data.get('title') or ''
        content = request.data.get('content') or ''
        publish = bool(request.data.get('publish', False))
        image_files = request.FILES.getlist('images') or []

        if not title:
            return error_response("标题不能为空")
        if not content:
            return error_response("内容不能为空")
        if not image_files:
            return error_response("缺少图片文件")

        dynamic_id = str(uuid.uuid4())
        # 保存动态主体
        Dynamic.objects.create(
            id=dynamic_id,
            title=title[:30],
            content=content,
            publish=publish,
            creator=str(request.user.id),
            origin="用户创建",
        )

        # 保存上传的图片文件并建立关联顺序
        def save_one_file(file_obj, index):
            try:
                orig_name = getattr(file_obj, 'name', '')
                ext = os.path.splitext(orig_name)[1] if orig_name else ''
                if not ext:
                    ct = getattr(file_obj, 'content_type', '') or ''
                    if 'jpeg' in ct or 'jpg' in ct:
                        ext = '.jpg'
                    elif 'png' in ct:
                        ext = '.png'
                    elif 'gif' in ct:
                        ext = '.gif'
                    elif 'webp' in ct:
                        ext = '.webp'
                    else:
                        ext = '.jpg'
                img_id = str(uuid.uuid4())
                filename = f"{img_id}{ext}"
                file_path = os.path.join(IMG_PATH, filename)
                with open(file_path, 'wb') as f:
                    for chunk in file_obj.chunks():
                        f.write(chunk)
                # 创建 Image 记录
                pil = PILImage.open(file_path)
                width, height = pil.size
                spec = {'format': pil.format, 'mode': pil.mode}
                Image(id=img_id, img_name=filename, img_path=IMG_PATH, origin="动态关联", height=height, creator=request.user.id, width=width,
                      spec=spec).save()
                # 建立 DynamicImage 关联并设置顺序
                DynamicImage(dynamic_id=str(dynamic_id), image_id=img_id, index=index).save()
            except Exception as e:
                logger.error(f"保存图片失败: {str(e)}")

        for idx, f in enumerate(image_files, start=1):
            save_one_file(f, idx)
        return ok_response("创建成功")


class DynamicDeleteView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="删除指定动态",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'dynamic_id': openapi.Schema(type=openapi.TYPE_STRING, description='动态ID'),
            },
            required=['dynamic_id']
        ),
    )
    def post(self, request):
        dynamic_id = request.data.get('dynamic_id')
        if not dynamic_id:
            return error_response("缺少动态ID")
        try:
            # 先处理关联图片：若不再被其他动态引用则删除图片记录与文件
            associations = DynamicImage.objects.filter(dynamic_id=dynamic_id).order_by('index')
            for assoc in associations:
                try:
                    other_exists = DynamicImage.objects.filter(image_id=assoc.image_id).exclude(dynamic_id=dynamic_id).exists()
                    if not other_exists:
                        try:
                            img = Image.objects.get(id=assoc.image_id)
                            base_path = img.img_path or IMG_PATH
                            file_path = os.path.join(base_path, img.img_name)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            img.delete()
                        except Image.DoesNotExist:
                            pass
                        except Exception as e:
                            logger.error(f"删除图片文件或记录失败: {str(e)}")
                except Exception:
                    logger.error(traceback.format_exc())
                    continue
            # 删除关联关系与动态
            DynamicImage.objects.filter(dynamic_id=dynamic_id).delete()
            Dynamic.objects.filter(id=dynamic_id).delete()
            return ok_response("删除成功")
        except Exception as e:
            logger.error(traceback.format_exc())
            return error_response(f"删除失败: {str(e)}")


class DynamicBatchDeleteView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="批量删除动态",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'ids': openapi.Schema(type=openapi.TYPE_ARRAY, items=openapi.Items(type=openapi.TYPE_STRING), description='动态ID列表'),
            },
            required=['ids']
        ),
    )
    def post(self, request):
        ids = request.data.get('ids') or []
        if not isinstance(ids, list) or not ids:
            return error_response("ids 必须是非空数组")
        try:
            # 找出所有拟删除动态所关联的图片
            associations = DynamicImage.objects.filter(dynamic_id__in=ids)
            image_ids = set(associations.values_list('image_id', flat=True))
            # 若图片不再被其他动态引用，则删除图片记录与文件
            for img_id in image_ids:
                try:
                    still_referenced = DynamicImage.objects.filter(image_id=img_id).exclude(dynamic_id__in=ids).exists()
                    if not still_referenced:
                        try:
                            img = Image.objects.get(id=img_id)
                            base_path = img.img_path or IMG_PATH
                            file_path = os.path.join(base_path, img.img_name)
                            if os.path.exists(file_path):
                                os.remove(file_path)
                            img.delete()
                        except Image.DoesNotExist:
                            pass
                        except Exception as e:
                            logger.error(f"删除图片文件或记录失败: {str(e)}")
                except Exception:
                    logger.error(traceback.format_exc())
                    continue
            # 删除关联关系与动态
            DynamicImage.objects.filter(dynamic_id__in=ids).delete()
            Dynamic.objects.filter(id__in=ids).delete()
            return ok_response({
                'deleted': len(ids),
                'requested': len(ids)
            })
        except Exception:
            logger.error(traceback.format_exc())
            return error_response("批量删除失败")
