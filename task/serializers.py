from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ScheduledTask
from django_apscheduler.models import DjangoJob, DjangoJobExecution
from datetime import timedelta


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """任务列表序列化器"""
    creator_name = serializers.SerializerMethodField()
    next_run_time = serializers.SerializerMethodField()
    last_run_time = serializers.SerializerMethodField()
    last_run_status = serializers.SerializerMethodField()
    latest_run_result = serializers.SerializerMethodField()

    class Meta:
        model = ScheduledTask
        fields = [
            'id', 'job', 'name', 'description', 'job_type', 'is_active',
            'creator', 'creator_name', 'created_at', 'updated_at',
            'need_args', 'execution_time', 'interval', 'next_run_time', 'last_run_time',
            'last_run_status', 'latest_run_result'
        ]
        read_only_fields = ['job', 'created_at', 'updated_at']

    def get_creator_name(self, obj):
        try:
            user = User.objects.get(id=obj.creator)
            return user.username
        except User.DoesNotExist:
            return obj.creator

    def get_next_run_time(self, obj):
        return obj.next_run_time

    def get_last_run_time(self, obj):
        return obj.last_run_time

    def get_last_run_status(self, obj):
        return obj.last_run_status

    def get_latest_run_result(self, obj):
        """获取任务最近十次的运行结果"""
        if not obj.job:
            return []
        
        # 获取最近10次的执行记录
        executions = DjangoJobExecution.objects.filter(
            job_id=obj.job.id
        ).order_by('-run_time')[:10]
        
        results = []
        for execution in executions:
            result = {
                'id': execution.id,
                'run_time': execution.run_time,
                'status': execution.status,
                'duration': float(execution.duration) if execution.duration else None,
                'finished_time': execution.finished,
                'exception': execution.exception,
                'traceback': execution.traceback,
                'is_success': execution.status == DjangoJobExecution.SUCCESS,
                'is_error': execution.status == DjangoJobExecution.ERROR,
            }
            results.append(result)
        
        return results


class ScheduledTaskCreateSerializer(serializers.ModelSerializer):
    """任务创建序列化器"""

    class Meta:
        model = ScheduledTask
        fields = [
            'name', 'description', 'job_type', 'is_active',
            'need_args', 'execution_time', 'interval'
        ]

    def validate(self, data):
        job_type = data.get('job_type')

        if job_type == 'interval':
            if not data.get('interval'):
                raise serializers.ValidationError("周期性任务必须指定间隔秒数")
        elif job_type == 'date':
            if not data.get('execution_time'):
                raise serializers.ValidationError("定时任务必须指定执行时间")

        return data

    def create(self, validated_data):

        # 设置创建者
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['creator'] = str(request.user.id)

        # 创建DjangoJob
        django_job = DjangoJob.objects.create(
            id=f"task_{validated_data['name']}",
            job_state=b'',  # 空的job状态
            next_run_time=validated_data.get('execution_time')
        )

        # 创建ScheduledTask
        validated_data['job'] = django_job
        task = ScheduledTask.objects.create(**validated_data)

        return task
