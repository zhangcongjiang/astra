import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ok_response, error_response
from text.models import Graph
from .models import Asset, AssetInfo
from .serializers import (
    AssetSerializer, AssetDetailSerializer, AssetCreateUpdateSerializer,
    AssetInfoCreateSerializer, AssetUpdateSerializer
)

logger = logging.getLogger("asset")


class AssetPagination(PageNumberPagination):
    """素材集分页器"""
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 1000


class AssetListView(generics.ListAPIView):
    """分页查询素材集列表"""
    queryset = Asset.objects.all().order_by('-create_time')
    serializer_class = AssetSerializer
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = AssetPagination

    @swagger_auto_schema(
        operation_summary="分页查询素材集列表",
        operation_description="获取素材集列表，支持分页和条件筛选",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_INTEGER),
            openapi.Parameter('creator', openapi.IN_QUERY, description="创建者筛选", type=openapi.TYPE_STRING),
            openapi.Parameter('name', openapi.IN_QUERY, description="素材集名称（模糊匹配）", type=openapi.TYPE_STRING),
        ]
    )
    def get(self, request, *args, **kwargs):
        try:
            # 获取查询参数
            creator = request.query_params.get('creator', request.user.id)
            name = request.query_params.get('name')

            # 构建查询条件
            queryset = self.queryset

            # 按创建者筛选
            if creator:
                queryset = queryset.filter(creator=creator)

            # 按名称模糊匹配筛选
            if name:
                queryset = queryset.filter(set_name__icontains=name)

            # 分页处理
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(queryset, request)

            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return ok_response(data=paginator.get_paginated_response(serializer.data).data)

            serializer = self.get_serializer(queryset, many=True)
            return ok_response(data=serializer.data)
        except Exception as e:
            logger.error(f"获取素材集列表失败: {str(e)}")
            return error_response("获取素材集列表失败")


class AssetDetailView(APIView):
    """查看素材集详情"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="查看素材集详情",
        operation_description="根据ID获取素材集详细信息，按类型分组返回所有素材",
        responses={
            200: AssetDetailSerializer,
            404: "素材集不存在"
        }
    )
    def get(self, request, asset_id):
        try:
            asset = Asset.objects.get(id=asset_id)
            serializer = AssetDetailSerializer(asset)
            return ok_response(data=serializer.data)
        except Asset.DoesNotExist:
            return error_response("素材集不存在")
        except Exception as e:
            logger.error(f"获取素材集详情失败: {str(e)}")
            return error_response("获取素材集详情失败")


class AssetDeleteView(APIView):
    """删除素材集"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="删除素材集",
        operation_description="删除指定的素材集及其所有素材",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_id': openapi.Schema(type=openapi.TYPE_STRING, description='素材集ID')
            },
            required=['asset_id']
        )
    )
    def post(self, request):
        asset_id = request.data.get('asset_id')
        if not asset_id:
            return error_response("素材集ID不能为空")

        try:
            asset = Asset.objects.get(id=asset_id)
            # 删除素材集中的所有素材信息
            AssetInfo.objects.filter(set_id=str(asset_id)).delete()
            # 删除素材集
            asset.delete()
            return ok_response("素材集删除成功")
        except Asset.DoesNotExist:
            return error_response("素材集不存在")
        except Exception as e:
            logger.error(f"删除素材集失败: {str(e)}")
            return error_response("删除素材集失败")


class AssetCreateView(APIView):
    """新建素材集"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="新建素材集",
        operation_description="创建新的素材集",
        request_body=AssetCreateUpdateSerializer
    )
    def post(self, request):
        serializer = AssetCreateUpdateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                asset = serializer.save()
                return ok_response(
                    data=AssetSerializer(asset).data
                )
            except Exception as e:
                logger.error(f"创建素材集失败: {str(e)}")
                return error_response("创建素材集失败")
        return error_response(f"参数验证失败{serializer.errors}")


class AssetUpdateView(APIView):
    """编辑素材集 - 只允许更新名称"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="编辑素材集名称",
        operation_description="更新素材集名称，只允许修改名称字段",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_id': openapi.Schema(type=openapi.TYPE_STRING, description='素材集ID'),
                'set_name': openapi.Schema(type=openapi.TYPE_STRING, description='新的素材集名称')
            },
            required=['asset_id', 'set_name']
        )
    )
    def post(self, request):
        asset_id = request.data.get('asset_id')
        set_name = request.data.get('set_name')

        if not asset_id:
            return error_response("素材集ID不能为空")

        if not set_name:
            return error_response("素材集名称不能为空")

        try:
            asset = Asset.objects.get(id=asset_id)
            # 使用专门的更新序列化器，只允许更新名称
            serializer = AssetUpdateSerializer(asset, data={'set_name': set_name}, partial=True)
            if serializer.is_valid():
                asset = serializer.save()
                return ok_response(
                    data=AssetSerializer(asset).data,
                    message="素材集名称更新成功"
                )
            return error_response(f"参数验证失败: {serializer.errors}")
        except Asset.DoesNotExist:
            return error_response("素材集不存在")
        except Exception as e:
            logger.error(f"更新素材集失败: {str(e)}")
            return error_response("更新素材集失败")


class AssetInfoCreateView(APIView):
    """素材集内增加素材"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="素材集内增加素材",
        operation_description="向指定素材集添加不同类型的素材",
        request_body=AssetInfoCreateSerializer
    )
    def post(self, request):
        serializer = AssetInfoCreateSerializer(data=request.data)
        if serializer.is_valid():
            try:
                # 验证素材集是否存在
                set_id = serializer.validated_data['set_id']
                if not Asset.objects.filter(id=set_id).exists():
                    return error_response("素材集不存在")

                asset_info = serializer.save()
                return ok_response(
                    data={
                        'id': asset_info.id,
                        'set_id': asset_info.set_id,
                        'resource_id': asset_info.resource_id,
                        'asset_type': asset_info.asset_type,
                        'index': asset_info.index
                    },

                )
            except Exception as e:
                logger.error(f"添加素材失败: {str(e)}")
                return error_response("添加素材失败")
        return error_response("参数验证失败")


class AssetInfoDeleteView(APIView):
    """删除素材集中的素材"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="删除素材集中的素材",
        operation_description="从素材集中移除指定素材",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_info_id': openapi.Schema(type=openapi.TYPE_STRING, description='素材信息ID')
            },
            required=['asset_info_id']
        )
    )
    def post(self, request):
        asset_info_id = request.data.get('asset_info_id')
        if not asset_info_id:
            return error_response("素材信息ID不能为空")

        try:
            asset_info = AssetInfo.objects.get(id=asset_info_id)
            if asset_info.asset_type == 'text':
                Graph.objects.filter(id=asset_info.resource_id).delete()
            asset_info.delete()
            return ok_response("素材删除成功")
        except AssetInfo.DoesNotExist:
            return error_response("素材信息不存在")
        except Exception as e:
            logger.error(f"删除素材失败: {str(e)}")
            return error_response("删除素材失败")


class AssetInfoReorderView(APIView):
    """调整素材顺序"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="调整素材顺序",
        operation_description="重新排列素材集中素材的顺序",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_info_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description='按新顺序排列的素材信息ID列表'
                )
            },
            required=['asset_info_ids']
        )
    )
    def post(self, request):
        asset_info_ids = request.data.get('asset_info_ids', [])
        if not asset_info_ids:
            return error_response("素材ID列表不能为空")

        try:
            # 批量更新顺序
            for i, asset_info_id in enumerate(asset_info_ids, 1):
                AssetInfo.objects.filter(id=asset_info_id).update(index=i)

            return ok_response("素材顺序调整成功")
        except Exception as e:
            logger.error(f"调整素材顺序失败: {str(e)}")
            return error_response("调整素材顺序失败")


class TextAssetCreateView(APIView):
    """创建文本类型素材并添加到素材集（支持批量创建）"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="批量创建文本素材",
        operation_description="批量创建文本素材并添加到指定素材集",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'set_id': openapi.Schema(type=openapi.TYPE_STRING, description='素材集ID'),
                'texts': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(
                        type=openapi.TYPE_OBJECT,
                        properties={
                            'text': openapi.Schema(type=openapi.TYPE_STRING, description='文本内容'),
                            'creator': openapi.Schema(type=openapi.TYPE_STRING, description='创建者（可选）')
                        },
                        required=['text']
                    ),
                    description='文本素材列表'
                ),
                'creator': openapi.Schema(type=openapi.TYPE_STRING, description='默认创建者（当单个文本未指定时使用）')
            },
            required=['set_id', 'texts']
        )
    )
    def post(self, request):
        set_id = request.data.get('set_id')
        texts = request.data.get('texts', [])
        default_creator = request.data.get('creator', request.user.username if hasattr(request.user, 'username') else '')

        if not set_id:
            return error_response("素材集ID不能为空")
        if not texts or not isinstance(texts, list):
            return error_response("文本列表不能为空")
        if len(texts) == 0:
            return error_response("至少需要提供一个文本内容")

        try:
            # 验证素材集是否存在
            if not Asset.objects.filter(id=set_id).exists():
                return error_response("素材集不存在")

            created_assets = []

            # 使用事务确保批量操作的原子性
            from django.db import transaction
            with transaction.atomic():
                for text_data in texts:
                    text_content = text_data.get('text')
                    creator = text_data.get('creator', default_creator)

                    if not text_content:
                        raise ValueError("文本内容不能为空")

                    # 创建文本记录
                    from text.models import Graph
                    graph = Graph.objects.create(
                        text=text_content,
                        creator=creator
                    )

                    # 创建素材信息记录
                    asset_info = AssetInfo.objects.create(
                        set_id=set_id,
                        resource_id=str(graph.id),
                        asset_type='text'
                    )

                    created_assets.append({
                        'id': asset_info.id,
                        'set_id': asset_info.set_id,
                        'resource_id': asset_info.resource_id,
                        'asset_type': asset_info.asset_type,
                        'index': asset_info.index,
                        'text_detail': {
                            'id': graph.id,
                            'text': graph.text,
                            'creator': graph.creator,
                            'create_time': graph.create_time
                        }
                    })

            return ok_response(
                data={
                    'created_count': len(created_assets),
                    'assets': created_assets
                },
                message=f"成功创建{len(created_assets)}个文本素材"
            )
        except ValueError as e:
            return error_response(str(e))
        except Exception as e:
            logger.error(f"批量创建文本素材失败: {str(e)}")
            return error_response("批量创建文本素材失败")


class TextAssetUpdateView(APIView):
    """更新文本类型素材"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="更新文本素材",
        operation_description="更新指定的文本素材内容",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_info_id': openapi.Schema(type=openapi.TYPE_STRING, description='素材信息ID'),
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='新的文本内容')
            },
            required=['asset_info_id', 'text']
        )
    )
    def post(self, request):
        asset_info_id = request.data.get('asset_info_id')
        new_text = request.data.get('text')

        if not asset_info_id:
            return error_response("素材信息ID不能为空")
        if not new_text:
            return error_response("文本内容不能为空")

        try:
            # 获取素材信息
            asset_info = AssetInfo.objects.get(id=asset_info_id)

            # 验证是否为文本类型
            if asset_info.asset_type != 'text':
                return error_response("该素材不是文本类型")

            # 更新文本内容
            from text.models import Graph
            graph = Graph.objects.get(id=asset_info.resource_id)
            graph.text = new_text
            graph.save()

            return ok_response(
                "文本素材更新成功"
            )
        except AssetInfo.DoesNotExist:
            return error_response("素材信息不存在")
        except Graph.DoesNotExist:
            return error_response("文本记录不存在")
        except Exception as e:
            logger.error(f"更新文本素材失败: {str(e)}")
            return error_response("更新文本素材失败")


class ResourceDetailView(APIView):
    """根据素材类型和ID查询素材详情"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="查询素材详情",
        operation_description="根据素材类型和ID查询素材的详细信息",
        manual_parameters=[
            openapi.Parameter('resource_type', openapi.IN_QUERY, description="素材类型 (image/video/audio)",
                              type=openapi.TYPE_STRING, required=True,
                              enum=['image', 'video', 'audio']),
            openapi.Parameter('resource_id', openapi.IN_QUERY, description="素材ID",
                              type=openapi.TYPE_STRING, required=True)
        ],
        responses={
            200: openapi.Response(
                description="素材详情",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'id': openapi.Schema(type=openapi.TYPE_STRING, description='素材ID'),
                        'name': openapi.Schema(type=openapi.TYPE_STRING, description='素材名称'),
                        'creator': openapi.Schema(type=openapi.TYPE_STRING, description='创建者'),
                        'create_time': openapi.Schema(type=openapi.TYPE_STRING, description='创建时间'),
                        'type': openapi.Schema(type=openapi.TYPE_STRING, description='素材类型'),
                        'spec': openapi.Schema(type=openapi.TYPE_OBJECT, description='规格信息'),
                        'extra_info': openapi.Schema(type=openapi.TYPE_OBJECT, description='额外信息')
                    }
                )
            ),
            400: "参数错误",
            404: "素材不存在"
        }
    )
    def get(self, request):
        resource_type = request.query_params.get('resource_type')
        resource_id = request.query_params.get('resource_id')

        # 参数验证
        if not resource_type:
            return error_response("素材类型不能为空")
        if not resource_id:
            return error_response("素材ID不能为空")
        if resource_type not in ['image', 'video', 'audio']:
            return error_response("素材类型必须是 image、video 或 audio")

        try:
            if resource_type == 'image':
                from image.models import Image
                resource = Image.objects.get(id=resource_id)
                data = {
                    'id': str(resource.id),
                    'name': resource.img_name,
                    'creator': resource.creator,
                    'create_time': resource.create_time.isoformat(),
                    'type': 'image',
                    'spec': resource.spec,
                    'extra_info': {
                        'path': resource.img_path,
                        'width': resource.width,
                        'height': resource.height,
                        'origin': resource.origin,
                        'category': resource.category
                    }
                }
            elif resource_type == 'video':
                from video.models import VideoAsset
                resource = VideoAsset.objects.get(id=resource_id)
                data = {
                    'id': str(resource.id),
                    'name': resource.asset_name,
                    'creator': resource.creator,
                    'create_time': resource.create_time.isoformat(),
                    'type': 'video',
                    'spec': resource.spec,
                    'extra_info': {
                        'duration': resource.duration,
                        'orientation': resource.orientation,
                        'origin': resource.origin
                    }
                }
            elif resource_type == 'audio':
                from voice.models import Sound
                resource = Sound.objects.get(id=resource_id)
                data = {
                    'id': str(resource.id),
                    'name': resource.name,
                    'creator': resource.creator,
                    'create_time': resource.create_time.isoformat(),
                    'type': 'audio',
                    'spec': resource.spec,
                    'extra_info': {
                        'path': resource.sound_path,
                        'singer': resource.singer,
                        'desc': resource.desc,
                        'category': resource.category
                    }
                }

            return ok_response(data=data)

        except Exception as e:
            # 处理不同类型的异常
            if 'DoesNotExist' in str(type(e)):
                return error_response(f"{resource_type}素材不存在")
            else:
                logger.error(f"查询{resource_type}素材详情失败: {str(e)}")
                return error_response(f"查询{resource_type}素材详情失败")
