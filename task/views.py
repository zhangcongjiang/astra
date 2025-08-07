from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated

from common.response import ok_response, error_response
from .models import ScheduledTask
from .serializers import ScheduledTaskSerializer, ScheduledTaskCreateSerializer


class ScheduledTaskViewSet(viewsets.GenericViewSet):
    """
    任务管理视图集
    
    提供任务的创建、查询、更新、删除等功能
    只使用GET和POST方法
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ScheduledTask.objects.all().order_by('-created_at')
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ScheduledTaskCreateSerializer
        return ScheduledTaskSerializer
    
    @swagger_auto_schema(
        operation_summary="获取任务列表",
        operation_description="获取所有任务列表，支持按状态和类型筛选",
        manual_parameters=[
            openapi.Parameter(
                'is_active',
                openapi.IN_QUERY,
                description="任务状态筛选 (true/false)",
                type=openapi.TYPE_BOOLEAN,
                required=False
            ),
            openapi.Parameter(
                'job_type',
                openapi.IN_QUERY,
                description="任务类型筛选 (scheduled/periodic/manual)",
                type=openapi.TYPE_STRING,
                required=False
            ),
        ],
        responses={
            200: openapi.Response(
                description="获取成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(type=openapi.TYPE_OBJECT)
                        )
                    }
                )
            )
        }
    )
    def list(self, request, *args, **kwargs):
        """获取所有任务列表"""
        try:
            queryset = self.filter_queryset(self.get_queryset())
            
            # 支持按状态筛选
            is_active = request.query_params.get('is_active')
            if is_active is not None:
                queryset = queryset.filter(is_active=is_active.lower() == 'true')
            
            # 支持按任务类型筛选
            job_type = request.query_params.get('job_type')
            if job_type:
                queryset = queryset.filter(job_type=job_type)
            
            # 分页
            page = self.paginate_queryset(queryset)
            if page is not None:
                serializer = self.get_serializer(page, many=True)
                return self.get_paginated_response(serializer.data)
            
            serializer = self.get_serializer(queryset, many=True)
            return ok_response(data=serializer.data, message="获取任务列表成功")
            
        except Exception as e:
            return error_response(f"获取任务列表失败: {str(e)}")
    
    @swagger_auto_schema(
        operation_summary="创建任务",
        operation_description="创建新的定时任务",
        request_body=ScheduledTaskCreateSerializer,
        responses={
            200: openapi.Response(
                description="创建成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(description="参数错误")
        }
    )
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """创建新任务"""
        try:
            serializer = self.get_serializer(data=request.data)
            if serializer.is_valid():
                task = serializer.save()
                response_serializer = ScheduledTaskSerializer(task)
                return ok_response(
                    data=response_serializer.data,
                    message="任务创建成功"
                )
            else:
                return error_response(
                    "数据验证失败"
                )
        except Exception as e:
            return error_response(f"创建任务失败: {str(e)}")
    
    @swagger_auto_schema(
        operation_summary="获取任务详情",
        operation_description="根据ID获取单个任务的详细信息",
        responses={
            200: openapi.Response(
                description="获取成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            404: openapi.Response(description="任务不存在")
        }
    )
    def retrieve(self, request, *args, **kwargs):
        """获取单个任务详情"""
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance)
            return ok_response(data=serializer.data, message="获取任务详情成功")
        except Exception as e:
            return error_response(f"获取任务详情失败: {str(e)}")
    
    @swagger_auto_schema(
        operation_summary="更新任务",
        operation_description="使用POST方法更新任务信息",
        request_body=ScheduledTaskCreateSerializer,
        responses={
            200: openapi.Response(
                description="更新成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            400: openapi.Response(description="参数错误"),
            404: openapi.Response(description="任务不存在")
        }
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def update_task(self, request, pk=None):
        """使用POST方法更新任务"""
        try:
            instance = self.get_object()
            serializer = ScheduledTaskCreateSerializer(instance, data=request.data, partial=True)
            
            if serializer.is_valid():
                task = serializer.save()
                response_serializer = ScheduledTaskSerializer(task)
                return ok_response(
                    data=response_serializer.data,
                    message="任务更新成功"
                )
            else:
                return error_response(
                    "数据验证失败"

                )
        except Exception as e:
            return error_response(f"更新任务失败: {str(e)}")
    
    @swagger_auto_schema(
        operation_summary="删除任务",
        operation_description="使用POST方法删除任务",
        responses={
            200: openapi.Response(
                description="删除成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息')
                    }
                )
            ),
            404: openapi.Response(description="任务不存在")
        }
    )
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def delete_task(self, request, pk=None):
        """使用POST方法删除任务"""
        try:
            instance = self.get_object()
            task_name = instance.name
            
            # 删除关联的DjangoJob
            if instance.job:
                instance.job.delete()
            
            # 删除任务本身
            instance.delete()
            
            return ok_response(data=f"任务 '{task_name}' 删除成功")
        except Exception as e:
            return error_response(f"删除任务失败: {str(e)}")
    
    @swagger_auto_schema(
        operation_summary="切换任务状态",
        operation_description="启用或禁用任务",
        responses={
            200: openapi.Response(
                description="状态切换成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(type=openapi.TYPE_OBJECT)
                    }
                )
            ),
            404: openapi.Response(description="任务不存在")
        }
    )
    @action(detail=True, methods=['post'])
    def toggle_status(self, request, pk=None):
        """切换任务启用/禁用状态"""
        try:
            task = self.get_object()
            task.is_active = not task.is_active
            task.save()
            
            status_text = "启用" if task.is_active else "禁用"
            serializer = ScheduledTaskSerializer(task)
            
            return ok_response(
                data=serializer.data,
                message=f"任务已{status_text}"
            )
        except Exception as e:
            return error_response(f"切换任务状态失败: {str(e)}")