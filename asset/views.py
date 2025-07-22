import logging

from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from common.response import ok_response, error_response
from .models import Asset, AssetInfo
from .serializers import (
    AssetSerializer, AssetDetailSerializer, AssetCreateUpdateSerializer,
    AssetInfoCreateSerializer
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
    authentication_classes = [TokenAuthentication]
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
        # 获取查询参数
        creator = request.query_params.get('creator')
        name = request.query_params.get('name')
        
        # 构建查询条件
        queryset = self.queryset
        
        # 按创建者筛选
        if creator:
            queryset = queryset.filter(creator=creator)
        
        # 按名称模糊匹配筛选
        if name:
            queryset = queryset.filter(set_name__icontains=name)
        
        self.queryset = queryset
        return super().get(request, *args, **kwargs)


class AssetDetailView(APIView):
    """查看素材集详情"""
    authentication_classes = [TokenAuthentication]
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
    authentication_classes = [TokenAuthentication]
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
    authentication_classes = [TokenAuthentication]
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
    """编辑素材集"""
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_summary="编辑素材集",
        operation_description="更新素材集信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'asset_id': openapi.Schema(type=openapi.TYPE_STRING, description='素材集ID'),
                'set_name': openapi.Schema(type=openapi.TYPE_STRING, description='素材集名称'),
                'creator': openapi.Schema(type=openapi.TYPE_STRING, description='创建者')
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
            serializer = AssetCreateUpdateSerializer(asset, data=request.data, partial=True)
            if serializer.is_valid():
                asset = serializer.save()
                return ok_response(
                    data=AssetSerializer(asset).data,

                )
            return error_response(f"参数验证失败{serializer.errors}")
        except Asset.DoesNotExist:
            return error_response("素材集不存在")
        except Exception as e:
            logger.error(f"更新素材集失败: {str(e)}")
            return error_response("更新素材集失败")


class AssetInfoCreateView(APIView):
    """素材集内增加素材"""
    authentication_classes = [TokenAuthentication]
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
    authentication_classes = [TokenAuthentication]
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
            asset_info.delete()
            return ok_response("素材删除成功")
        except AssetInfo.DoesNotExist:
            return error_response("素材信息不存在")
        except Exception as e:
            logger.error(f"删除素材失败: {str(e)}")
            return error_response("删除素材失败")


class AssetInfoReorderView(APIView):
    """调整素材顺序"""
    authentication_classes = [TokenAuthentication]
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
