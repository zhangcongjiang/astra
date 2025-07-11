import os
import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from astra.settings import LOGO_PATH
from common.response import ok_response, error_response
from .models import Tool


class ToolUploadView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser]

    @swagger_auto_schema(
        operation_description="上传新工具及logo图片",

        manual_parameters=[

            openapi.Parameter(
                'name', openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description='工具名称',
                required=True
            ),
            openapi.Parameter(
                'url', openapi.IN_FORM,
                type=openapi.TYPE_STRING,
                description='工具url',
                required=True
            ),
            openapi.Parameter(
                'logo',
                openapi.IN_FORM,
                type=openapi.TYPE_FILE,
                required=True,
                description='工具logo图片',
                collection_format='multi'
            ),
            openapi.Parameter(
                'category', openapi.IN_FORM,
                description="工具分类 (text: 文本工具, sound: 音频工具，image:图片工具，vidoe:视频工具,other:其他工具)",
                enum=['text', 'image', 'sound', 'video', 'other'],
                type=openapi.TYPE_STRING,
                required=True
            ),

        ],
        responses={
            201: openapi.Response(
                description="工具创建成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": {"id": "<uuid>"}
                    }
                }
            )
        }
    )
    def post(self, request, format=None):
        try:
            # 处理logo文件上传
            logo_file = request.FILES['logo']
            tool_id = str(uuid.uuid4())
            file_name = f"{tool_id}.png"
            file_path = os.path.join(LOGO_PATH, file_name)
            with open(file_path, 'wb+') as destination:
                for chunk in logo_file.chunks():
                    destination.write(chunk)

            # 创建工具记录
            tool = Tool.objects.create(
                id=tool_id,
                tool_name=request.data.get('name'),
                logo_path=file_name,
                origin='user',
                url=request.data.get('url'),
                category=request.data.get('category', 'other'),
                creator=request.data.get('creator', '')

            )

            return ok_response({
                'id': str(tool.id)
            })
        except Exception as e:
            return error_response(str(e))


class ToolCategoryView(APIView):
    def get(self, request):
        tools = Tool.objects.filter(category=request.query_params.get('category'))
        result = [{
            'id': tool.id,
            'name': tool.tool_name,
            'logo_path': request.build_absolute_uri(settings.MEDIA_URL + "logo/" + tool.logo_path),
            'url': tool.url,
            'category': tool.category,
            'create_time': tool.create_time
        } for tool in tools]
        return ok_response(result)
