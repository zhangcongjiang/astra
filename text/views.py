import os
import uuid

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

from astra.settings import ARTICLE_PATH
from common.response import error_response, ok_response
from .models import Text
from .serializers import TextSerializer, TextDetailSerializer, TextUploadSerializer

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'


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

            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # 创建数据库记录
            text = Text.objects.create(
                id=text_id,
                title=title,
                publish=False,
                creator=request.user.id  # 使用当前用户ID作为创建者
            )

            # 序列化返回数据
            response_serializer = TextSerializer(text)

            return ok_response(
                data=response_serializer.data,
            )

        except Exception as e:
            # 如果数据库操作失败，删除已保存的文件
            if file_path in locals() and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except Exception:
                    pass

            return error_response(f"文章上传失败: {str(e)}")
