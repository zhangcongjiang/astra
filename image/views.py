import logging
import mimetypes
import os
import uuid
from datetime import datetime

from PIL import Image as PILImage
from django.db.models import Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from astra.settings import IMG_PATH, BKG_PATH
from common.response import error_response, ok_response
from image.models import Image, ImageTags
from image.serializers import ImageSerializer, ImageBindTagsSerializer
from tag.models import Tag

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'
IMG_DIR = {
    'normal': IMG_PATH,
    'background': BKG_PATH
}

logger = logging.getLogger("image")


class StandardResultsSetPagination(PageNumberPagination):
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


class ImageUploadView(generics.CreateAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_serializer_class(self):
        return None

    @swagger_auto_schema(
        operation_description="上传图片",
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM, description="图片文件", type=openapi.TYPE_FILE, required=True
            ),
            openapi.Parameter(
                'category', openapi.IN_FORM, description="图片分类 (normal: 普通图片, background: 背景图片)", enum=['normal', 'background'],
                type=openapi.TYPE_STRING, required=True
            ),
        ],
        responses={
            200: openapi.Response(
                description="图片上传成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": "image_path",
                        "msg": "success"
                    }
                }
            )
        }
    )
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        category = request.data.get('category')
        if not file:
            return error_response("未提供图片")
        valid_mime_types = ['image/jpeg', 'image/png', 'image/jpg']
        mime_type, _ = mimetypes.guess_type(file.name)

        if mime_type not in valid_mime_types:
            return error_response("只支持jpeg、png、jpg格式图片")
        if category not in ['normal', 'background']:
            return error_response("分类必须是 normal 或 background")

        pil_image = PILImage.open(file)
        width, height = pil_image.size
        image_format = pil_image.format
        image_mode = pil_image.mode

        filename = f"{str(uuid.uuid4())}.{file.name.split('.')[-1]}"
        file_path = os.path.join(IMG_DIR.get(category), filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        spec = {
            'format': image_format,
            'mode': image_mode
        }
        Image(img_name=filename, category=category, width=int(width), height=int(height), spec=spec).save()
        logger.info(f"image {filename} 上传成功")
        return ok_response("ok")


class ImageListView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ImageSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        start_datetime_str = self.request.query_params.get('start_datetime', '1970-01-01T00:00:00')
        end_datetime_str = self.request.query_params.get('end_datetime', datetime.now().strftime(TIME_FORMAT))
        tag_id = self.request.query_params.get('tag_id', '')
        sort_by = self.request.query_params.get('sort_by', 'create_time')
        order = self.request.query_params.get('order', 'asc')
        category = self.request.query_params.get('category', 'normal')
        try:
            start_datetime = timezone.make_aware(datetime.strptime(start_datetime_str, TIME_FORMAT))
            end_datetime = timezone.make_aware(datetime.strptime(end_datetime_str, TIME_FORMAT))
        except ValueError:
            return Image.objects.none()

        if end_datetime <= start_datetime:
            return Image.objects.none()

        query = Q()

        if tag_id:
            try:
                tag = Tag.objects.get(id=tag_id)
                if tag.parent == '':
                    child_tags = Tag.objects.filter(parent=tag).values_list('id', flat=True)
                    image_ids = ImageTags.objects.filter(tag_id__in=child_tags).values_list('image_id', flat=True)
                else:
                    image_ids = ImageTags.objects.filter(tag_id=tag_id).values_list('image_id', flat=True)
                query &= Q(id__in=image_ids)
            except Tag.DoesNotExist:
                return Image.objects.none()
        query &= Q(create_time__range=(start_datetime, end_datetime))
        query &= Q(category=category)

        if order == 'desc':
            sort_by = f'-{sort_by}'
        queryset = Image.objects.filter(query).order_by(sort_by)

        return queryset

    @swagger_auto_schema(
        operation_description="分页查询满足条件的图片",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('start_datetime', openapi.IN_QUERY, description="开始时间 (格式: YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_datetime', openapi.IN_QUERY, description="结束时间 (格式: YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="图片分类 (normal: 普通图片, background: 背景图片)", type=openapi.TYPE_STRING,
                              default='normal'),
            openapi.Parameter('tag_id', openapi.IN_QUERY, description="标签ID", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="排序字段 (默认: create_time)", type=openapi.TYPE_STRING),
            openapi.Parameter('order', openapi.IN_QUERY, description="排序顺序 (asc 或 desc, 默认: asc)", type=openapi.TYPE_STRING),
        ],
        responses={200: ImageSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ok_response(serializer.data)


class BindTagsToImageAPIView(APIView):
    @swagger_auto_schema(
        operation_description="给图片绑定多个标签",
        request_body=ImageBindTagsSerializer,
        responses={
            200: "绑定成功",
            400: "无效的输入",
            404: "图片或标签不存在",
        },
    )
    def post(self, request):
        # 验证输入数据
        serializer = ImageBindTagsSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("无效的输入")

        image_id = serializer.validated_data['image_id']
        tag_ids = serializer.validated_data['tag_ids']

        # 检查图片是否存在
        if not Image.objects.filter(id=image_id).exists():
            return error_response("图片不存在")

        # 绑定标签
        for tag_id in tag_ids:
            # 检查标签是否存在（假设标签模型为 Tag）
            if not Tag.objects.filter(id=tag_id).exists():
                return error_response(f"标签id：{tag_id}不存在")

            # 创建 ImageTags 记录
            ImageTags.objects.create(image_id=image_id, tag_id=tag_id)

        return ok_response("绑定成功")


class DeleteImagesAPIView(APIView):
    @swagger_auto_schema(
        operation_description="批量删除图片及其关联的标签记录",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'image_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                    description='图片ID列表'
                ),
            },
            required=['image_ids']
        ),
        responses={
            200: "删除成功",
            400: "无效的输入",
        },
    )
    def post(self, request):
        # 获取请求数据
        image_ids = request.data.get('image_ids')

        # 验证输入
        if not image_ids or not isinstance(image_ids, list):
            return error_response("输入参数错误，image_ids必须是一个非空的列表")

        # 批量删除图片及其关联的标签记录
        try:
            # 删除关联的标签记录
            ImageTags.objects.filter(image_id__in=image_ids).delete()

            # 删除图片
            images = Image.objects.filter(id__in=image_ids)
            for image in images:
                os.remove(os.path.join(IMG_DIR.get(image.category)) + image.img_name)
                image.delete()
                logger.info(f"image {image.img_name} 删除成功")
            return ok_response("删除成功")

        except Exception as e:
            return error_response(f"删除失败：{str(e)}")


class DeleteImageTagAPIView(APIView):
    @swagger_auto_schema(
        operation_description="删除图片绑定的单个标签",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'image_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='图片ID'),
                'tag_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='标签ID'),
            },
            required=['image_id', 'tag_id']
        ),
        responses={
            200: "删除成功",
            404: "图片或标签绑定关系不存在",
        },
    )
    def post(self, request):
        # 获取请求数据
        image_id = request.data.get('image_id')
        tag_id = request.data.get('tag_id')

        if not image_id or not tag_id:
            return error_response("image_id 和 tag_id 不能为空")

        try:
            # 查找图片和标签的绑定关系
            image_tag = ImageTags.objects.get(image_id=image_id, tag_id=tag_id)

            # 删除绑定关系
            image_tag.delete()

            return ok_response("解绑成功")

        except ImageTags.DoesNotExist:
            return error_response("不存在绑定关系")


class ImageDetailView(generics.RetrieveAPIView):
    queryset = Image.objects.all()
    serializer_class = ImageSerializer
    lookup_field = 'id'  # 根据 UUID 查找图片

    @swagger_auto_schema(
        operation_description="查看图片详情",
        responses={
            200: openapi.Response(
                description="图片详情",
                schema=ImageSerializer
            ),
            404: "图片不存在",
        }
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)
