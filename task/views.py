import os
import subprocess
import uuid
from datetime import timedelta

from django.db import transaction
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework import viewsets
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.permissions import IsAuthenticated

from astra.settings import SCRIPTS_PATH
from common.response import ok_response, error_response
from .models import ScheduledTask
from .serializers import ScheduledTaskSerializer, ScheduledTaskCreateSerializer


# 在文件开头添加分页类定义
class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'pageSize'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return ok_response(data={
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class ScheduledTaskViewSet(viewsets.GenericViewSet):
    """
    任务管理视图集

    提供任务的创建、查询、更新、删除等功能
    只使用GET和POST方法
    """
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = ScheduledTask.objects.all().order_by('-created_at')
    parser_classes = [JSONParser, MultiPartParser, FormParser]  # 支持文件上传
    pagination_class = StandardResultsSetPagination

    def get_serializer_class(self):
        if self.action == 'create':
            return ScheduledTaskCreateSerializer
        return ScheduledTaskSerializer

    @swagger_auto_schema(
        operation_summary="获取任务列表",
        operation_description="获取所有任务列表，支持按状态和类型筛选，支持分页",
        manual_parameters=[
            openapi.Parameter(
                'page',
                openapi.IN_QUERY,
                description="页码",
                type=openapi.TYPE_INTEGER,
                default=1
            ),
            openapi.Parameter(
                'pageSize',
                openapi.IN_QUERY,
                description="每页条目数",
                type=openapi.TYPE_INTEGER,
                default=20
            ),
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
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'count': openapi.Schema(type=openapi.TYPE_INTEGER, description='总数量'),
                                'next': openapi.Schema(type=openapi.TYPE_STRING, description='下一页链接'),
                                'previous': openapi.Schema(type=openapi.TYPE_STRING, description='上一页链接'),
                                'results': openapi.Schema(
                                    type=openapi.TYPE_ARRAY,
                                    items=openapi.Schema(type=openapi.TYPE_OBJECT),
                                    description='任务列表数据'
                                )
                            }
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
        operation_summary="创建新的定时任务",
        operation_description="创建新的定时任务，支持上传Python脚本文件",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'name': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="任务名称"
                ),
                'description': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="任务描述"
                ),
                'job_type': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    enum=['scheduled', 'periodic', 'manual'],
                    description="任务类型"
                ),
                'script_file': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format=openapi.FORMAT_BINARY,
                    description="Python脚本文件（.py格式）"
                ),
                'interval': openapi.Schema(
                    type=openapi.TYPE_INTEGER,
                    description="间隔秒数（周期性任务必填）"
                ),
                'execution_time': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="执行时间（定时任务必填，格式：YYYY-MM-DD HH:MM:SS）"
                ),
                'is_active': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="是否激活"
                ),
                'need_args': openapi.Schema(
                    type=openapi.TYPE_BOOLEAN,
                    description="是否需要参数"
                ),
            },
            required=['name', 'job_type']
        ),
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
            )
        }
    )
    def create(self, request, *args, **kwargs):
        """创建新任务"""
        script_name = f"{uuid.uuid4().hex}.py"
        file_path = os.path.join(SCRIPTS_PATH, script_name)
        try:
            with transaction.atomic():
                serializer = self.get_serializer(data=request.data)

                serializer.is_valid(raise_exception=True)
                script_file = request.FILES.get('script_file')
                if not script_file:
                    return error_response("必须提供脚本文件")
                if not script_file.name.endswith('.py'):
                    raise error_response("脚本文件必须是.py格式")

                # 保存文件
                with open(file_path, 'wb+') as destination:
                    for chunk in script_file.chunks():
                        destination.write(chunk)
                task_name = request.data.get('name')
                job_type = request.data.get('job_type')
                description = request.data.get('description', '')
                need_args = request.data.get('need_args')
                if need_args == 'true':
                    need_args = True
                else:
                    need_args = False
                is_active = request.data.get('is_active')
                if is_active == 'true':
                    is_active = True
                else:
                    is_active = False
                execution_time = request.data.get('execution_time', None)
                interval = int(request.data.get('interval', 0))
                creator = request.user.id

                ScheduledTask(name=task_name, description=description, job_type=job_type, need_args=need_args, script_name=script_name,
                              creator=creator, is_active=is_active, execution_time=execution_time, interval=timedelta(seconds=interval)).save()

                return ok_response(
                    "任务创建成功"
                )
        except Exception as e:
            if os.path.exists(file_path):
                os.remove(file_path)
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
            )
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

    @swagger_auto_schema(
        operation_summary="手动执行任务",
        operation_description="手动执行指定的任务，支持传入执行参数",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'task_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="任务ID"
                ),
                'execution_args': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description="执行参数（可选，会覆盖任务默认参数）"
                ),
            },
            required=['task_id']
        ),
        responses={
            200: openapi.Response(
                description="执行成功",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'code': openapi.Schema(type=openapi.TYPE_INTEGER, description='状态码'),
                        'message': openapi.Schema(type=openapi.TYPE_STRING, description='消息'),
                        'data': openapi.Schema(
                            type=openapi.TYPE_OBJECT,
                            properties={
                                'task_id': openapi.Schema(type=openapi.TYPE_STRING, description='任务ID'),
                                'task_name': openapi.Schema(type=openapi.TYPE_STRING, description='任务名称'),
                                'execution_id': openapi.Schema(type=openapi.TYPE_STRING, description='执行ID'),
                                'command': openapi.Schema(type=openapi.TYPE_STRING, description='执行命令'),
                                'status': openapi.Schema(type=openapi.TYPE_STRING, description='执行状态'),
                                'output': openapi.Schema(type=openapi.TYPE_STRING, description='执行输出'),
                                'error': openapi.Schema(type=openapi.TYPE_STRING, description='错误信息')
                            }
                        )
                    }
                )
            ),
            400: openapi.Response(description="参数错误"),
            404: openapi.Response(description="任务不存在")
        }
    )
    @action(detail=False, methods=['post'])
    def execute_manual(self, request):
        """手动执行任务"""
        try:
            task_id = request.data.get('task_id')
            execution_args = request.data.get('execution_args', '')

            if not task_id:
                return error_response("任务ID不能为空")

            # 获取任务
            try:
                task = ScheduledTask.objects.get(id=task_id)
            except ScheduledTask.DoesNotExist:
                return error_response("任务不存在")

            # 构建执行命令
            script_path = os.path.join(SCRIPTS_PATH, task.script_name)

            # 检查脚本文件是否存在
            if not os.path.exists(script_path):
                return error_response(f"脚本文件不存在: {task.script_name}")

            # 构建命令参数
            cmd = ['python', script_path]
            if task.need_args:
                cmd.append(execution_args)

            # 生成执行ID
            execution_id = str(uuid.uuid4())

            # 执行脚本
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5分钟超时
                    cwd=SCRIPTS_PATH
                )

                # 准备返回数据
                response_data = {
                    'task_id': str(task.id),
                    'task_name': task.name,
                    'execution_id': execution_id,
                    'command': ' '.join(cmd),
                    'status': 'success' if result.returncode == 0 else 'failed',
                    'output': result.stdout,
                    'error': result.stderr if result.stderr else None
                }

                if result.returncode == 0:
                    return ok_response(
                        data=response_data,
                        message="任务执行成功"
                    )
                else:
                    return error_response(
                        f"任务执行失败，退出码: {result.returncode}",
                    )

            except subprocess.TimeoutExpired:
                return error_response(
                    "任务执行超时（超过5分钟）",

                )
            except Exception as e:
                return error_response(
                    f"执行脚本时发生错误: {str(e)}"
                )

        except Exception as e:
            return error_response(f"手动执行任务失败: {str(e)}")
