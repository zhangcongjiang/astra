from django.http import FileResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import BusinessException
from common.redis_tools import ControlRedis
from common.response import error_response, ok_response
from video.models import VideoProcess
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
            return ok_response(metadata)
        except Exception as e:
            return error_response(str(e))

    @swagger_auto_schema(
        operation_description="根据模板生成视频",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            required=['template_id', 'title', 'speaker', 'data'],
            properties={
                'template_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频模板标识'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='标题'),
                'speaker': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='音色选项'),
                'beginning': openapi.Schema(type=openapi.TYPE_OBJECT, description='视频开头部分'),
                'data': openapi.Schema(type=openapi.TYPE_OBJECT, description='生成素材的内容'),
                'ending': openapi.Schema(type=openapi.TYPE_OBJECT, description='视频结尾部分'),
            }

        ),
        responses={
            200: openapi.Response(
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
            )
        }
    )
    def post(self, request, format=None):
        try:
            data = request.data
            data['creator'] = 'admin'

            result = template.generate_video(data)

            return ok_response(result)
        except Exception:
            return error_response("视频生成失败")


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
            video_path = template.download(video_id)

            # 使用 FileResponse 直接返回视频文件
            response = FileResponse(open(video_path, 'rb'), content_type='video/mp4')
            response['Content-Disposition'] = f'attachment; filename="{video_id}.mp4"'
            return response
        except BusinessException as e:
            return error_response(str(e))
        except FileNotFoundError:
            return error_response(
                "视频文件未找到"
            )


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
        try:
            video_process = VideoProcess.objects.get(id=video_id)
            if video_process.process == 'PROCESS':
                return ok_response({
                    'process': redis_control.get_key(video_id)
                })
            elif video_process.process == 'PREPARATION':
                return ok_response({
                    'preparation': 0
                })
            elif video_process.process == 'SUCCESS':
                return ok_response({
                    'success': 0
                })
            elif video_process.process == 'FAIL':
                return ok_response({
                    'fail': 0
                })
        except Exception:
            return error_response("获取视频进度失败")
