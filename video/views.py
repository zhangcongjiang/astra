import mimetypes
import os
import uuid

from django.http import HttpResponse
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.templatetags.static import static

from drf_yasg.utils import swagger_auto_schema
from drf_yasg import openapi
from rest_framework.authentication import TokenAuthentication

from common.exceptions import BusinessException
from common.redis_tools import ControlRedis
from video.templates.video_template import VideoTemplate

template = VideoTemplate()
template.get_templates()

redis_control = ControlRedis()


class TemplateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="查询所有支持的视频模板",
        responses={
            200: openapi.Response(
                description="Success",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "success",
                        "data": [
                            {
                                "name": "MultipleImgToVideo",
                                "desc": "多张图文成片，适用于盘点、排行类视频",
                                "parameters": {

                                }
                            },
                            {
                                "name": "SignalImgToVideo",
                                "desc": "单张图片生成视频，适用于国风、鸡汤类视频",
                                "parameters": {

                                }
                            }
                        ]
                    }
                }
            ),
            500: openapi.Response(
                description="Internal Server Error",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "fail",
                        "data": ""
                    }
                }
            ),
        }
    )
    def get(self, request, format=None):
        try:

            metadata = template.get_templates()
            return Response({
                'code': 0,
                "message": "success",
                "data": metadata
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'code': 1,
                "message": "fail",
                "data": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @swagger_auto_schema(
        operation_description="根据模板生成视频",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['template_id', 'title', 'orientation', 'data'],
            properties={
                'template_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频模板标识'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='标题'),
                'orientation': openapi.Schema(type=openapi.TYPE_STRING, description='横版视频或者竖版视频'),
                'cover': openapi.Schema(type=openapi.TYPE_STRING, description='视频封面'),
                'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='生成素材的内容')
            }

        ),
        responses={
            201: openapi.Response(
                description="Template created successfully",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "Template created successfully",
                        "data": {
                            "name": "NewTemplate",
                            "parameters": {}
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="Bad Request",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "Invalid data",
                        "data": ""
                    }
                }
            ),
            500: openapi.Response(
                description="Internal Server Error",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "fail",
                        "data": ""
                    }
                }
            ),
        }
    )
    def post(self, request, format=None):
        try:
            data = request.data
            data['creator'] = 'admin'

            new_template = template.generate_video(data)

            return Response({
                'code': 0,
                "message": "Template created successfully",
                "data": new_template
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({
                'code': 1,
                "message": "fail",
                "data": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VideoView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'video_id', openapi.IN_PATH, description="ID of the video",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={200: 'application/zip'}
    )
    def get(self, request, video_id, *args, **kwargs):
        # 根据 video_id 查找相应的视频和图片文件
        # 这里假设文件名是根据 video_id 动态生成的
        try:
            zip_buffer = template.download(video_id)
            response = HttpResponse(zip_buffer, content_type='application/zip')
            response['Content-Disposition'] = f'attachment; filename="{video_id}.zip"'
            return response
        except BusinessException as e:
            return Response({
                'code': 1,
                "message": "fail",
                "data": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VideoProgressView(APIView):
    @swagger_auto_schema(
        manual_parameters=[
            openapi.Parameter(
                'video_id', openapi.IN_PATH, description="ID of the video",
                type=openapi.TYPE_STRING, required=True
            )
        ],
        responses={
            200: openapi.Response(
                description="Audio uploaded successfully",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": "99",
                        "msg": "success"
                    }
                }
            ),
        }
    )
    def get(self, request, video_id, *args, **kwargs):
        if redis_control.exists_key(video_id):
            return Response({'code': 0, 'message': 'success', 'data': redis_control.get_key(video_id)}, status=status.HTTP_200_OK)
        else:
            return Response({'code': 1, 'data': "invalid video id", "message": "fail"}, status=status.HTTP_404_NOT_FOUND)


