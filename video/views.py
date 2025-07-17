from django.http import FileResponse
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.exceptions import BusinessException
from common.redis_tools import ControlRedis
from common.response import error_response, ok_response
from video.models import Video
from video.serializers import VideoSerializer
from video.templates.video_template import VideoTemplate

from video.models import Video
from video.serializers import VideoDetailSerializer
from common.response import ok_response, error_response

template = VideoTemplate()
template.get_templates()

redis_control = ControlRedis()


class CustomPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return ok_response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class TemplateView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="查询所有支持的视频模板",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('name', openapi.IN_QUERY, description="名称", type=openapi.TYPE_STRING),
            openapi.Parameter('orientation', openapi.IN_QUERY, description="视频模板方向", type=openapi.TYPE_STRING),
            openapi.Parameter('tag_id', openapi.IN_QUERY, description="标签id", type=openapi.TYPE_STRING),

        ],
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
            tag_id = request.query_params.get('tag_id', '')
            name = request.query_params.get('name', '')
            orientation = request.query_params.get('orientation', '')

            metadata = template.filter_templates(name, orientation, tag_id)

            # 手动实例化分页器
            paginator = CustomPagination()

            # 获取分页结果
            page = paginator.paginate_queryset(metadata, request)
            if page is not None:
                return paginator.get_paginated_response(page)

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
            return error_response("视频生成失败,请查看后台日志！")


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


class VideoListView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="分页查询视频列表",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('page_size', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('title', openapi.IN_QUERY, description="视频标题", type=openapi.TYPE_STRING),
            openapi.Parameter('creator', openapi.IN_QUERY, description="创建者", type=openapi.TYPE_STRING),
            openapi.Parameter('result', openapi.IN_QUERY, description="状态", type=openapi.TYPE_STRING),
            openapi.Parameter('start_time', openapi.IN_QUERY, description="开始时间(YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_time', openapi.IN_QUERY, description="结束时间(YYYY-MM-DD)", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Success",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "success",
                        "data": {
                            "count": 100,
                            "next": "http://example.com/api/videos/?page=2",
                            "previous": None,
                            "results": [
                                {"id": 1, "title": "视频1", "creator": "user1"},
                                {"id": 2, "title": "视频2", "creator": "user2"}
                            ]
                        }
                    }
                }
            )
        }
    )
    def get(self, request):
        try:
            # 获取查询参数
            title = request.query_params.get('title')
            creator = request.query_params.get('creator')
            start_time = request.query_params.get('start_time')
            end_time = request.query_params.get('end_time')
            status = request.query_params.get('result')

            # 构建查询条件
            queryset = Video.objects.all()
            if title:
                queryset = queryset.filter(title__icontains=title)
            if creator:
                queryset = queryset.filter(creator=creator)
            if status:
                queryset = queryset.filter(result=status)
            if start_time and end_time:
                queryset = queryset.filter(
                    create_time__range=(start_time, end_time)
                )

            # 分页处理
            paginator = PageNumberPagination()
            paginator.page_size = request.query_params.get('page_size', 10)
            page = paginator.paginate_queryset(queryset, request)

            # 序列化数据
            serializer = VideoSerializer(page, many=True)

            # 返回分页响应
            return ok_response({
                'count': paginator.page.paginator.count,
                'next': paginator.get_next_link(),
                'previous': paginator.get_previous_link(),
                'results': serializer.data
            })

        except Exception as e:
            return error_response(str(e))


class VideoDetailView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="获取视频详细信息",
        manual_parameters=[
            openapi.Parameter('video_id', openapi.IN_PATH, description="视频ID", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="Success",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "success",
                        "data": {
                            "id": 1,
                            "title": "示例视频",
                            "creator": "user1",
                            "parameters": {
                                "data": "{\"width\":1920,\"height\":1080}"
                            }
                        }
                    }
                }
            )
        }
    )
    def get(self, request, video_id):
        try:
            video = Video.objects.get(id=video_id)
            serializer = VideoDetailSerializer(video)
            return ok_response(serializer.data)
        except Video.DoesNotExist:
            return error_response("视频不存在")
        except Exception as e:
            return error_response(str(e))
