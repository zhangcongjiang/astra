import logging
import os

import shutil
import traceback
import uuid
from urllib.parse import urlparse
import re
import markdown
from bs4 import BeautifulSoup

import requests
from PIL import Image as PILImage
from django.http import HttpResponse, Http404
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from asset.models import AssetInfo, Asset
from astra.settings import ARTICLE_PATH, IMG_PATH
from common.response import ok_response, error_response
from image.models import Image
from video.models import VideoAsset
from voice.models import Sound
from .models import Text, Graph
from .serializers import TextSerializer, TextDetailSerializer, TextUploadSerializer

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
logger = logging.getLogger("text")


def process_images_in_content(content, image_set_id):
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
            Image(id=img_id, img_name=new_filename, img_path=IMG_PATH, origin="图文关联", height=height, width=width, spec=spec).save()
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


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return ok_response(data={
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class TextListView(generics.ListAPIView):
    """文章列表接口"""
    authentication_classes = [TokenAuthentication]
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
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'publish', openapi.IN_QUERY,
                description="发布状态筛选 (true/false)",
                type=openapi.TYPE_BOOLEAN
            ),
            openapi.Parameter(
                'start_time', openapi.IN_QUERY,
                description="开始时间 (格式: YYYY-MM-DDTHH:MM:SS)",
                type=openapi.TYPE_STRING
            ),
            openapi.Parameter(
                'end_time', openapi.IN_QUERY,
                description="结束时间 (格式: YYYY-MM-DDTHH:MM:SS)",
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
        creator = self.request.query_params.get('creator')
        if creator:
            queryset = queryset.filter(creator=creator)

        # 发布状态筛选
        publish = self.request.query_params.get('publish')
        if publish is not None:
            publish_bool = publish.lower() == 'true'
            queryset = queryset.filter(publish=publish_bool)

        # 时间范围筛选
        start_time = self.request.query_params.get('start_time')
        end_time = self.request.query_params.get('end_time')

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
    authentication_classes = [TokenAuthentication]
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
    authentication_classes = [TokenAuthentication]
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
    authentication_classes = [TokenAuthentication]
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
            # 验证UUID格式
            uuid.UUID(text_id)
        except ValueError:
            raise Http404("无效的文章ID格式")

        try:
            text = Text.objects.get(id=text_id)
            file_path = os.path.join(ARTICLE_PATH, f"{text_id}.md")

            if not os.path.exists(file_path):
                raise Http404("文章文件不存在")

            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{text.title}.md"'
                return response

        except Text.DoesNotExist:
            raise Http404("文章不存在")
        except Exception as e:
            raise Http404(f"下载文章失败: {str(e)}")


class TextUploadView(APIView):
    """文章上传接口"""
    authentication_classes = [TokenAuthentication]
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

            # 处理文件内容中的图片
            processed_content = process_images_in_content(file_content, text_id)

            # 解析Markdown内容为Graph对象
            try:
                parse_markdown_to_graphs(file_content, text_id)

            except Exception as e:
                logger.error(f"解析Markdown段落失败: {str(e)}")
                # 如果高级解析失败，使用简单解析

            # 保存处理后的内容到文件
            with open(file_path, 'w', encoding='utf-8') as destination:
                destination.write(processed_content)

            # 创建数据库记录
            text = Text.objects.create(
                id=text_id,
                title=title[:30],
                publish=False,
                creator=request.user.id  # 使用当前用户ID作为创建者
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
    authentication_classes = [TokenAuthentication]
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

        # 处理content中的图片
        if content:
            content = process_images_in_content(content, title)

        try:
            if text_id:
                return self._update_text(text_id, title, content, request.user.id)
            else:
                return self._create_text(title, content, request.user.id)
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

            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)

            # 创建数据库记录
            Text.objects.create(
                id=text_id,
                title=title,
                creator=user_id
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
                # 更新文件内容
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(content)

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
    md_str = re.sub(r'!\[[^\]]*\]\([^\)]+\)', '', content)
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
