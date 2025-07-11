from rest_framework import serializers
from .models import ScheduledTask
from django_apscheduler.models import DjangoJobExecution
import importlib
from django.conf import settings


class JobExecutionSerializer(serializers.ModelSerializer):
    status_display = serializers.SerializerMethodField()

    class Meta:
        model = DjangoJobExecution
        fields = [
            'id', 'run_time', 'duration',
            'status_display', 'exception', 'traceback'
        ]
        read_only_fields = fields

    def get_status_display(self, obj):
        return "成功" if obj.status else "失败"


class ScheduledTaskSerializer(serializers.ModelSerializer):
    next_run_time = serializers.DateTimeField(read_only=True)
    last_run_time = serializers.DateTimeField(read_only=True)
    last_run_status = serializers.CharField(read_only=True)
    trigger_config = serializers.CharField(read_only=True)
    job_function = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = ScheduledTask
        fields = [
            'job', 'name', 'job_type', 'description', 'is_active',
            'job_args', 'job_kwargs', 'created_at', 'updated_at',
            'next_run_time', 'last_run_time', 'last_run_status',
            'trigger_config', 'job_function'
        ]
        read_only_fields = [
            'id', 'created_at', 'updated_at', 'next_run_time',
            'last_run_time', 'last_run_status', 'trigger_config'
        ]

    def validate_job_function(self, value):
        try:
            module_name, func_name = value.rsplit('.', 1)
            module = importlib.import_module(module_name)
            getattr(module, func_name)  # 验证函数存在
            return value
        except (ImportError, AttributeError, ValueError) as e:
            raise serializers.ValidationError(f"无效的任务函数路径: {str(e)}")

    def validate(self, data):
        job_type = data.get('job_type')
        job_kwargs = data.get('job_kwargs', {})

        if job_type == 'cron' and not job_kwargs.get('cron'):
            raise serializers.ValidationError({
                "job_kwargs": "Cron任务必须提供cron表达式"
            })

        if job_type == 'interval' and not job_kwargs.get('seconds'):
            raise serializers.ValidationError({
                "job_kwargs": "周期性任务必须提供间隔秒数"
            })

        return data


class TaskDetailSerializer(serializers.ModelSerializer):
    next_run_time = serializers.DateTimeField(read_only=True)
    status = serializers.SerializerMethodField()
    trigger_config = serializers.CharField(read_only=True)
    execution_history = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledTask
        fields = [
            'job', 'name', 'description', 'job_type', 'status',
            'is_active', 'created_at', 'updated_at', 'next_run_time',
            'trigger_config', 'job_args', 'job_kwargs', 'execution_history'
        ]
        read_only_fields = fields

    def get_status(self, obj):
        return "运行中" if obj.is_active else "已暂停"

    def get_execution_history(self, obj):
        executions = obj.job.executions.order_by('-run_time')[:10]
        return JobExecutionSerializer(executions, many=True).data

    def to_representation(self, instance):
        data = super().to_representation(instance)
        request = self.context.get('request')

        # 获取错误详情显示配置
        error_settings = getattr(settings, 'APSCHEDULER_DISPLAY_ERROR_DETAILS', {
            'staff': True,
            'user': False,
            'public': False
        })

        show_details = False
        if request:
            if request.user.is_staff and error_settings.get('staff', True):
                show_details = True
            elif request.user.is_authenticated and error_settings.get('user', False):
                show_details = True
            elif error_settings.get('public', False):
                show_details = True

        # 对非授权用户隐藏错误详情
        if not show_details:
            for execution in data['execution_history']:
                if execution['status_display'] == '失败':
                    execution['exception'] = "执行失败，详情已隐藏"
                    execution['traceback'] = None

        return data