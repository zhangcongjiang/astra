from rest_framework import serializers
from django.contrib.auth.models import User
from .models import ScheduledTask
from django_apscheduler.models import DjangoJob
from datetime import timedelta


class ScheduledTaskSerializer(serializers.ModelSerializer):
    """任务列表序列化器"""
    creator_name = serializers.SerializerMethodField()
    next_run_time = serializers.SerializerMethodField()
    last_run_time = serializers.SerializerMethodField()
    last_run_status = serializers.SerializerMethodField()
    command_line = serializers.SerializerMethodField()
    
    class Meta:
        model = ScheduledTask
        fields = [
            'job', 'name', 'description', 'job_type', 'is_active',
            'creator', 'creator_name', 'created_at', 'updated_at',
            'script_path', 'script_args', 'need_args',
            'run_date', 'interval', 'next_run_time', 'last_run_time',
            'last_run_status', 'command_line'
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
    
    def get_command_line(self, obj):
        return obj.command_line


class ScheduledTaskCreateSerializer(serializers.ModelSerializer):
    """任务创建序列化器"""
    interval_seconds = serializers.IntegerField(write_only=True, required=False, help_text="间隔秒数（用于周期性任务）")
    
    class Meta:
        model = ScheduledTask
        fields = [
            'name', 'description', 'job_type', 'is_active',
            'script_path', 'script_args', 'need_args',
            'run_date', 'interval_seconds'
        ]
    
    def validate(self, data):
        job_type = data.get('job_type')
        
        if job_type == 'interval':
            if not data.get('interval_seconds'):
                raise serializers.ValidationError("周期性任务必须指定间隔秒数")
        elif job_type == 'date':
            if not data.get('run_date'):
                raise serializers.ValidationError("定时任务必须指定执行时间")
        
        return data
    
    def create(self, validated_data):
        # 处理间隔时间
        interval_seconds = validated_data.pop('interval_seconds', None)
        if interval_seconds:
            validated_data['interval'] = timedelta(seconds=interval_seconds)
        
        # 设置创建者
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            validated_data['creator'] = str(request.user.id)
        
        # 创建DjangoJob
        django_job = DjangoJob.objects.create(
            id=f"task_{validated_data['name']}",
            job_state=b'',  # 空的job状态
            next_run_time=validated_data.get('run_date')
        )
        
        # 创建ScheduledTask
        validated_data['job'] = django_job
        task = ScheduledTask.objects.create(**validated_data)
        
        return task