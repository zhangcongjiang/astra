import mimetypes
import os
import uuid
from datetime import datetime

from django.db.models import Q
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from astra.settings import IMG_PATH
from common.response import error_response, ok_response
from image.models import Image, ImageTags
from image.serializers import ImageSerializer, BindTagsSerializer
from tag.models import Tag


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

    @swagger_auto_schema(
        operation_description="上传图片",
        manual_parameters=[
            openapi.Parameter(
                'file', openapi.IN_FORM, description="Image file to upload", type=openapi.TYPE_FILE, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Image uploaded successfully",
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
        if not file:
            return error_response("未提供图片")
        valid_mime_types = ['image/jpeg', 'image/png', 'image/jpg']
        mime_type, _ = mimetypes.guess_type(file.name)

        if mime_type not in valid_mime_types:
            return error_response("只支持jpeg、png、jpg格式图片")
        upload_dir = IMG_PATH
        filename = f"{str(uuid.uuid4())}.{file.name.split('.')[-1]}"
        file_path = os.path.join(upload_dir, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)
        Image(img_name=filename).save()

        return ok_response("ok")


class ImageListView(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = ImageSerializer
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="分页查询满足条件的图片",
        responses={200: ImageSerializer(many=True)},
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码r", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('start_datetime', openapi.IN_QUERY, description="开始时间，(格式：YYYY-MM-DDTHH:MM:SS)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('end_datetime', openapi.IN_QUERY, description="结束时间，(格式：YYYY-MM-DDTHH:MM:SS)",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('tag_id', openapi.IN_QUERY, description="标签id", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description='排序字段 (默认: create_time)', type=openapi.TYPE_STRING),
            openapi.Parameter('order', openapi.IN_QUERY, description='排序顺序 (asc 或 desc, 默认: asc)', type=openapi.TYPE_STRING)
        ]
    )
    def get_queryset(self):
        start_datetime_str = self.request.query_params.get('start_datetime', '1970-01-01T00:00:00')
        end_datetime_str = self.request.query_params.get('end_datetime', datetime.now().strftime('%Y-%m-%dT%H:%M:%S'))
        tag_id = int(self.request.query_params.get('tag_id', ''))
        sort_by = self.request.query_params.get('sort_by', 'create_time')
        order = self.request.query_params.get('order', 'asc')
        try:
            start_datetime = datetime.strptime(start_datetime_str, '%Y-%m-%dT%H:%M:%S')
            end_datetime = datetime.strptime(end_datetime_str, '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            return error_response("时间格式要求：YYYY-MM-DDTHH:MM:SS")

        if end_datetime <= start_datetime:
            return error_response("结束时间不得早于开始时间")

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
                return error_response(f"标签id：{tag_id}不存在")
        query &= Q(date__range=(start_datetime, end_datetime))

        if order == 'desc':
            sort_by = f'-{sort_by}'
        queryset = Image.objects.filter(query).order_by(sort_by)

        return queryset

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
        request_body=BindTagsSerializer,
        responses={
            200: "绑定成功",
            400: "无效的输入",
            404: "图片或标签不存在",
        },
    )
    def post(self, request):
        # 验证输入数据
        serializer = BindTagsSerializer(data=request.data)
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


class DeleteImageAPIView(APIView):
    @swagger_auto_schema(
        operation_description="删除图片及其关联的标签记录",
        responses={
            200: "删除成功",
            404: "图片不存在",
        },
    )
    def delete(self, request, image_id):
        try:
            # 查找图片
            image = Image.objects.get(id=image_id)

            # 删除关联的标签记录
            ImageTags.objects.filter(image_id=image_id).delete()

            # 删除图片
            image.delete()

            return ok_response("删除成功")

        except Image.DoesNotExist:
            return error_response("图片不存在")
