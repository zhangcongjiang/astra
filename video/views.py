import logging
import os
import shutil
import uuid

from django.core.files.storage import default_storage
from django.http import FileResponse
from PIL import Image as PILImage
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from moviepy import VideoFileClip
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from astra.settings import TTS_PATH, VIDEO_PATH, IMG_PATH
from common.exceptions import BusinessException
from common.redis_tools import ControlRedis
from common.response import ok_response, error_response
from image.models import Image
from tag.models import Tag
from video.models import Video, Parameters, VideoAssetTags
from video.models import VideoAsset
from video.serializers import VideoDetailSerializer
from video.serializers import VideoSerializer, VideoAssetUploadSerializer, VideoAssetSerializer
from video.templates.video_template import VideoTemplate
from voice.models import Tts

template = VideoTemplate()
template.get_templates()

redis_control = ControlRedis()
logger = logging.getLogger("video")


class CustomPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return ok_response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class TemplateView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="查询所有支持的视频模板",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
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
            user = request.user.id

            result = template.generate_video(user, data)

            return ok_response(result)
        except Exception:
            return error_response("视频生成失败,请查看后台日志！")


class VideoView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
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
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="分页查询视频列表",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
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
            creator = request.query_params.get('creator', self.request.user.id)
            start_time = request.query_params.get('start_time')
            end_time = request.query_params.get('end_time')
            status = request.query_params.get('result')
            video_type = request.query_params.get('video_type')

            # 构建查询条件
            queryset = Video.objects.all().order_by('-create_time')
            if title:
                queryset = queryset.filter(title__icontains=title)
            if video_type:
                queryset = queryset.filter(video_type=video_type)
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
            paginator.page_size = request.query_params.get('pageSize', 10)
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


class VideoDeleteView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="删除视频",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频ID')
            },
            required=['video_id']
        ),
        responses={
            200: openapi.Response(
                description="Success",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "视频删除成功",
                        "data": None
                    }
                }
            ),
            404: openapi.Response(
                description="Video not found",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "视频不存在",
                        "data": None
                    }
                }
            )
        }
    )
    def post(self, request):
        try:
            video_id = request.data.get('video_id')
            if not video_id:
                return error_response("视频ID不能为空")

            # 查找视频
            try:
                video = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return error_response("视频不存在")

            # 删除封面图片
            cover = video.cover
            if cover:
                try:
                    cover_image = Image.objects.get(id=cover)
                    if os.path.exists(os.path.join(IMG_PATH, cover_image.img_name)):
                        os.remove(os.path.join(IMG_PATH, cover_image.img_name))
                    cover_image.delete()
                except Image.DoesNotExist:
                    pass

            # 删除tts数据
            video_ttses = Tts.objects.filter(video_id=video_id)
            for tts in video_ttses:
                os.remove(os.path.join(TTS_PATH, f"{tts.id}.{tts.format}"))
                tts.delete()
            try:
                # 删除剪映草稿
                draft_folder = template.get_draft_folder(request.user.id)
                if os.path.exists(os.path.join(draft_folder, video.title)):
                    shutil.rmtree(os.path.join(draft_folder, video.title))
                if os.path.exists(os.path.join(VIDEO_PATH, f"{video_id}.mp4")):
                    os.remove(os.path.join(VIDEO_PATH, f"{video_id}.mp4"))
            except Exception:
                return error_response("剪映草稿删除失败，你可能在剪映窗口中打开了本视频")
            # 删除视频记录
            video.delete()

            return ok_response(None, "视频删除成功")

        except Exception as e:
            return error_response(f"删除失败: {str(e)}")


class VideoDetailView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
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


class VideoAssetUploadView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="上传视频素材（自动获取名称和方向）",
        request_body=VideoAssetUploadSerializer,
        responses={
            200: openapi.Response('上传成功', VideoAssetSerializer),
            400: '请求参数错误',
            401: '未授权'
        }
    )
    def post(self, request):
        try:
            serializer = VideoAssetUploadSerializer(data=request.data)
            if not serializer.is_valid():
                return error_response("参数验证失败", serializer.errors)

            video_file = serializer.validated_data['video_file']
            user = request.user.id
            # 自动获取文件名（去掉扩展名）
            asset_name = os.path.splitext(video_file.name)[0]

            # 生成唯一文件名
            file_extension = os.path.splitext(video_file.name)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"

            # 保存文件到media/videos目录
            video_path = f"videos/{unique_filename}"
            saved_path = default_storage.save(video_path, video_file)
            full_path = default_storage.path(saved_path)

            # 获取视频信息（时长、分辨率等）
            try:
                with VideoFileClip(full_path) as clip:
                    duration = clip.duration
                    width = clip.w
                    height = clip.h

                    # 自动判断横版还是竖版
                    if width > height:
                        orientation = 'HORIZONTAL'  # 横版
                    else:
                        orientation = 'VERTICAL'  # 竖版

            except Exception as e:
                # 如果无法获取视频信息，删除已保存的文件
                default_storage.delete(saved_path)
                return error_response(f"视频文件处理失败: {str(e)}")

            # 创建VideoAsset记录
            video_asset = VideoAsset.objects.create(
                asset_name=asset_name,
                origin="用户上传",
                creator=user,
                duration=duration,
                orientation=orientation,
                spec={

                    'file_path': saved_path,
                    'file_size': video_file.size,
                    'original_name': video_file.name,
                    'width': width,
                    'height': height,
                    'resolution': f"{width}x{height}"
                }
            )

            return ok_response(
                VideoAssetSerializer(video_asset).data,
                "视频素材上传成功"
            )

        except Exception as e:
            return error_response(f"上传失败: {str(e)}")


class VideoAssetListView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description="获取视频素材列表",
        manual_parameters=[
            openapi.Parameter('name', openapi.IN_QUERY, description="素材名称（模糊查询）", type=openapi.TYPE_STRING),
            openapi.Parameter('orientation', openapi.IN_QUERY, description="视频方向", type=openapi.TYPE_STRING, enum=['HORIZONTAL', 'VERTICAL']),
            openapi.Parameter('creator', openapi.IN_QUERY, description="创建人", type=openapi.TYPE_STRING),
            openapi.Parameter('start_time', openapi.IN_QUERY, description="开始时间 (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_time', openapi.IN_QUERY, description="结束时间 (YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_INTEGER),
        ],
        responses={
            200: openapi.Response('查询成功', VideoAssetSerializer(many=True)),
            401: '未授权'
        }
    )
    def get(self, request):
        try:
            queryset = VideoAsset.objects.all()

            # 名称模糊查询
            name = request.query_params.get('name')
            tag_id = self.request.query_params.get('tag_id', '')
            if name:
                queryset = queryset.filter(asset_name__icontains=name)

            # 方向筛选
            orientation = request.query_params.get('orientation')
            if orientation:
                queryset = queryset.filter(orientation=orientation)

            # 创建人筛选
            creator = request.query_params.get('creator', request.user.id)
            if creator:
                queryset = queryset.filter(creator__icontains=creator)

            if tag_id:
                try:
                    video_asset_ids = []
                    tag = Tag.objects.get(id=tag_id)
                    video_asset_ids.extend(VideoAssetTags.objects.filter(tag_id=tag_id).values_list('asset_id', flat=True))
                    if tag.parent == '':
                        child_tags = Tag.objects.filter(parent=tag).values_list('id', flat=True)
                        video_asset_ids.extend(VideoAssetTags.objects.filter(tag_id__in=child_tags).values_list('asset_id', flat=True))
                    else:
                        video_asset_ids.extend(VideoAssetTags.objects.filter(tag_id=tag_id).values_list('asset_id', flat=True))
                    queryset = queryset.filter(id__in=video_asset_ids)
                except Tag.DoesNotExist:
                    pass

            # 时间范围筛选
            start_time = request.query_params.get('start_time')
            end_time = request.query_params.get('end_time')
            if start_time:
                queryset = queryset.filter(create_time__date__gte=start_time)
            if end_time:
                queryset = queryset.filter(create_time__date__lte=end_time)

            # 按创建时间倒序排列
            queryset = queryset.order_by('-create_time')

            # 分页
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            if page is not None:
                serializer = VideoAssetSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = VideoAssetSerializer(queryset, many=True)
            return ok_response(serializer.data)

        except Exception as e:
            return error_response(f"查询失败: {str(e)}")


class VideoAssetDeleteView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="删除视频素材",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频素材ID')
            },
            required=['asset_id']
        ),
        responses={
            200: '删除成功',
            400: '请求参数错误',
            401: '未授权',
            404: '视频素材不存在'
        }
    )
    def post(self, request):
        try:
            asset_id = request.data.get('asset_id')
            if not asset_id:
                return error_response("缺少asset_id参数")

            try:
                video_asset = VideoAsset.objects.get(id=asset_id)
            except VideoAsset.DoesNotExist:
                return error_response("视频素材不存在")

            # 删除文件
            if video_asset.spec and 'file_path' in video_asset.spec:
                file_path = video_asset.spec['file_path']
                if default_storage.exists(file_path):
                    default_storage.delete(file_path)

            # 删除数据库记录
            video_asset.delete()

            return ok_response(None, "视频素材删除成功")

        except Exception as e:
            return error_response(f"删除失败: {str(e)}")


class VideoAssetPlayView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="播放视频素材",
        manual_parameters=[
            openapi.Parameter('asset_id', openapi.IN_PATH, description="视频素材ID", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: '返回视频文件',
            401: '未授权',
            404: '视频素材不存在'
        }
    )
    def get(self, request, asset_id):
        try:
            try:
                video_asset = VideoAsset.objects.get(id=asset_id)
            except VideoAsset.DoesNotExist:
                return error_response("视频素材不存在")

            # 获取文件路径
            if not video_asset.spec or 'file_path' not in video_asset.spec:
                return error_response("视频文件路径不存在")

            file_path = video_asset.spec['file_path']
            if not default_storage.exists(file_path):
                return error_response("视频文件不存在")

            # 返回文件响应
            full_path = default_storage.path(file_path)
            response = FileResponse(
                open(full_path, 'rb'),
                content_type='video/mp4',
                as_attachment=False
            )
            response['Content-Disposition'] = f'inline; filename="{video_asset.asset_name}"'
            return response

        except Exception as e:
            return error_response(f"播放失败: {str(e)}")


class VideoAssetEditView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="编辑视频素材名称",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频素材ID'),
                'asset_name': openapi.Schema(type=openapi.TYPE_STRING, description='新的素材名称'),
                'tag_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY, items=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'), description='新的标签ID列表'
                ),
            },
            required=['asset_id', 'asset_name']
        ),
        responses={
            200: openapi.Response(
                description="编辑成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "asset_name": "新的视频名称",
                            "origin": "horizontal",
                            "creator": "user123",
                            "duration": 30.5,
                            "orientation": "horizontal",
                            "create_time": "2024-01-01T12:00:00Z"
                        }
                    }
                }
            ),
            400: '请求参数错误',
            401: '未授权',
            404: '视频素材不存在'
        }
    )
    def post(self, request):
        try:
            asset_id = request.data.get('asset_id')
            asset_name = request.data.get('asset_name')
            tag_ids = request.data.get('tag_ids')
            try:
                video_asset = VideoAsset.objects.get(id=asset_id)
                if tag_ids:
                    VideoAssetTags.objects.filter(asset_id=asset_id).delete()
                    for tag in tag_ids:
                        VideoAssetTags.objects.create(asset_id=asset_id, tag_id=tag)
                if asset_name:
                    video_asset.asset_name = asset_name
                    video_asset.save()
            except VideoAsset.DoesNotExist:
                return error_response("视频素材不存在")

            # 更新素材名称

            # 返回更新后的数据
            response_serializer = VideoAssetSerializer(video_asset)
            return ok_response(response_serializer.data, "视频素材编辑成功")

        except Exception as e:
            return error_response(f"编辑失败: {str(e)}")


class DraftListView(APIView):
    """草稿视频列表接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = CustomPagination

    @swagger_auto_schema(
        operation_description="获取草稿视频列表",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=20),
            openapi.Parameter('template_id', openapi.IN_QUERY, description="模板ID", type=openapi.TYPE_STRING),
            openapi.Parameter('title', openapi.IN_QUERY, description="名称", type=openapi.TYPE_STRING),
            openapi.Parameter('creator', openapi.IN_QUERY, description="创建者", type=openapi.TYPE_STRING),
        ],
        responses={
            200: openapi.Response(
                description="获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": {
                            "count": 10,
                            "next": None,
                            "previous": None,
                            "results": [
                                {
                                    "id": "123e4567-e89b-12d3-a456-426614174000",
                                    "template_id": "template_001",
                                    "data": {"title": "示例标题"},
                                    "create_time": "2024-01-01T12:00:00Z",
                                    "update_time": "2024-01-01T12:00:00Z",
                                    "creator": "admin"
                                }
                            ]
                        }
                    }
                }
            ),
            401: '未授权'
        }
    )
    def get(self, request):
        try:
            from video.serializers import DraftSerializer

            queryset = Parameters.objects.all()

            # 模板ID筛选
            template_id = request.query_params.get('template_id')
            if template_id:
                queryset = queryset.filter(template_id=template_id)

            # 创建者筛选
            creator = request.query_params.get('creator', request.user.id)
            if creator:
                queryset = queryset.filter(creator=creator)
            title = request.query_params.get('title')
            if title:
                queryset = queryset.filter(title__icontains=title)

            # 按创建时间倒序排列
            queryset = queryset.order_by('-create_time')

            # 分页
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)
            if page is not None:
                serializer = DraftSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = DraftSerializer(queryset, many=True)
            return ok_response(serializer.data)

        except Exception as e:
            return error_response(f"获取草稿列表失败: {str(e)}")


class DraftDetailView(APIView):
    """草稿视频详情接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="获取草稿视频详情",
        manual_parameters=[
            openapi.Parameter('draft_id', openapi.IN_PATH, description="草稿ID", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: openapi.Response(
                description="获取成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "success",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "template_id": "template_001",
                            "data": {"title": "示例标题"},
                            "create_time": "2024-01-01T12:00:00Z",
                            "update_time": "2024-01-01T12:00:00Z",
                            "creator": "admin"
                        }
                    }
                }
            ),
            401: '未授权',
            404: '草稿不存在'
        }
    )
    def get(self, request, draft_id):
        try:
            from video.serializers import DraftSerializer

            try:
                draft = Parameters.objects.get(id=draft_id)
            except Parameters.DoesNotExist:
                return error_response("草稿不存在")

            serializer = DraftSerializer(draft)
            return ok_response(serializer.data)

        except Exception as e:
            return error_response(f"获取草稿详情失败: {str(e)}")


class DraftDeleteView(APIView):
    """草稿视频删除接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="删除草稿视频",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'draft_id': openapi.Schema(type=openapi.TYPE_STRING, description='草稿ID')
            },
            required=['draft_id']
        ),
        responses={
            200: openapi.Response(
                description="删除成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "草稿删除成功",
                        "data": None
                    }
                }
            ),
            400: '请求参数错误',
            401: '未授权',
            404: '草稿不存在'
        }
    )
    def post(self, request):
        try:
            draft_id = request.data.get('draft_id')
            if not draft_id:
                return error_response("缺少draft_id参数")

            try:
                draft = Parameters.objects.get(id=draft_id)
            except Parameters.DoesNotExist:
                return error_response("草稿不存在")

            # 删除草稿记录
            draft.delete()

            return ok_response(None, "草稿删除成功")

        except Exception as e:
            return error_response(f"删除草稿失败: {str(e)}")


class VideoUpdateView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="更新视频基础信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频ID'),
                'title': openapi.Schema(type=openapi.TYPE_STRING, description='视频标题', maxLength=30),
                'content': openapi.Schema(type=openapi.TYPE_STRING, description='视频内容描述'),
            },
            required=['video_id']
        ),
        responses={
            200: openapi.Response(
                description="更新成功",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "视频信息更新成功",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "更新后的标题",
                            "content": "更新后的内容",
                            "creator": "user1",
                            "create_time": "2024-01-01T12:00:00Z",
                            "update_time": "2024-01-01T12:30:00Z"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="请求参数错误",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "参数错误",
                        "data": None
                    }
                }
            ),
            404: openapi.Response(
                description="视频不存在",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "视频不存在",
                        "data": None
                    }
                }
            )
        }
    )
    def post(self, request):
        try:
            video_id = request.data.get('video_id')
            title = request.data.get('title')
            content = request.data.get('content')

            if not video_id:
                return error_response("视频ID不能为空")

            # 查找视频
            try:
                video = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return error_response("视频不存在", code=404)

            # 更新字段
            if title is not None:
                if len(title) > 30:
                    return error_response("标题长度不能超过30个字符")
                video.title = title

            if content is not None:
                video.content = content

            video.save()

            # 返回更新后的视频信息
            serializer = VideoDetailSerializer(video)
            return ok_response(serializer.data, "视频信息更新成功")

        except Exception as e:
            return error_response(f"更新失败: {str(e)}")


class VideoCoverUploadView(APIView):
    """视频封面上传接口"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="上传视频封面，如果已有封面则删除旧封面",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'video_id': openapi.Schema(type=openapi.TYPE_STRING, description='视频ID'),
                'cover': openapi.Schema(type=openapi.TYPE_FILE, description='封面图片文件'),
            },
            required=['video_id', 'cover']
        ),
        responses={
            200: openapi.Response(
                description="上传成功",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "封面上传成功",
                        "data": {
                            "id": "123e4567-e89b-12d3-a456-426614174000",
                            "title": "视频标题",
                            "cover": "covers/video_123e4567-e89b-12d3-a456-426614174000_cover.jpg",
                            "creator": "user1",
                            "create_time": "2024-01-01T12:00:00Z"
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="请求参数错误",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "参数错误",
                        "data": None
                    }
                }
            ),
            404: openapi.Response(
                description="视频不存在",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "视频不存在",
                        "data": None
                    }
                }
            )
        }
    )
    def post(self, request):
        try:
            video_id = request.data.get('video_id')
            cover_file = request.FILES.get('cover')

            if not video_id:
                return error_response("视频ID不能为空")

            if not cover_file:
                return error_response("封面文件不能为空")

            # 验证文件类型
            allowed_types = ['image/jpeg', 'image/jpg', 'image/png']
            if cover_file.content_type not in allowed_types:
                return error_response("不支持的文件类型，请上传 JPG、PNG格式的图片")

            # 验证文件大小 (5MB)
            max_size = 5 * 1024 * 1024
            if cover_file.size > max_size:
                return error_response("文件大小不能超过5MB")

            # 查找视频
            try:
                video = Video.objects.get(id=video_id)
            except Video.DoesNotExist:
                return error_response("视频不存在", code=404)

            # 删除旧封面文件
            if video.cover:
                try:
                    cover_img = Image.objects.get(id=video.cover)
                    cover_img.delete()
                    if os.path.exists(os.path.join(IMG_PATH, cover_img.img_name)):
                        os.remove(os.path.join(IMG_PATH, cover_img.img_name))
                except Image.DoesNotExist:
                    logger.info(f"Image {video.cover} not found")

            pil_image = PILImage.open(cover_file)
            width, height = pil_image.size
            image_format = pil_image.format
            image_mode = pil_image.mode

            cover_id = str(uuid.uuid4())
            filename = f"{str(uuid.uuid4())}.{cover_file.name.split('.')[-1]}"
            file_path = os.path.join(IMG_PATH, filename)

            with open(file_path, 'wb+') as destination:
                for chunk in cover_file.chunks():
                    destination.write(chunk)

            spec = {
                'format': image_format,
                'mode': image_mode
            }

            Image(
                id=cover_id,
                img_name=filename,
                category='normal',
                img_path=IMG_PATH,
                width=int(width),
                height=int(height),
                creator=request.user.id,
                spec=spec
            ).save()
            video.cover = cover_id
            video.save()

            return ok_response("封面上传成功")

        except Exception as e:
            return error_response(f"上传失败: {str(e)}")
