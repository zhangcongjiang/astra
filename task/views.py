import uuid
import importlib
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.triggers.date import DateTrigger
from .models import ScheduledTask
from .serializers import ScheduledTaskSerializer, TaskDetailSerializer
from scheduler.scheduler import get_scheduler

scheduler = get_scheduler()


class ScheduledTaskViewSet(viewsets.ModelViewSet):
    queryset = ScheduledTask.objects.select_related('job').prefetch_related(
        'job__executions'
    ).all()

    def get_serializer_class(self):
        if self.action == 'details':
            return TaskDetailSerializer
        return ScheduledTaskSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # 动态导入任务函数
        func_path = serializer.validated_data.pop('job_function')
        module_name, func_name = func_path.rsplit('.', 1)
        module = importlib.import_module(module_name)
        job_func = getattr(module, func_name)

        # 创建触发器
        job_type = serializer.validated_data['job_type']
        job_id = f"task_{uuid.uuid4().hex}"
        job_kwargs = serializer.validated_data.get('job_kwargs', {})

        if job_type == 'date':
            trigger = DateTrigger(run_date=job_kwargs.get('run_date'))
        elif job_type == 'interval':
            trigger = IntervalTrigger(**job_kwargs)
        elif job_type == 'cron':
            trigger = CronTrigger(**job_kwargs)

        # 添加任务到调度器
        job = scheduler.add_job(
            job_func,
            trigger=trigger,
            id=job_id,
            args=serializer.validated_data.get('job_args', []),
            kwargs=job_kwargs,
            replace_existing=True
        )

        # 创建任务元数据
        task = ScheduledTask.objects.create(
            job=job,
            **serializer.validated_data
        )

        # 如果不激活，则暂停任务
        if not serializer.validated_data['is_active']:
            scheduler.pause_job(job_id)

        return Response(
            ScheduledTaskSerializer(task).data,
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        partial = kwargs.pop('partial', False)
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)

        # 处理任务状态变化
        if 'is_active' in request.data:
            if request.data['is_active'] and not instance.is_active:
                scheduler.resume_job(instance.job.id)
            elif not request.data['is_active'] and instance.is_active:
                scheduler.pause_job(instance.job.id)

        # 处理任务配置更新
        if any(field in request.data for field in ['job_type', 'job_args', 'job_kwargs']):
            # 重新创建任务并删除旧任务
            new_data = {
                **serializer.validated_data,
                'job_function': f"{instance.job.func_ref.__module__}.{instance.job.func_ref.__name__}"
            }

            # 创建新任务
            new_serializer = self.get_serializer(data=new_data)
            new_serializer.is_valid(raise_exception=True)
            new_task = new_serializer.save()

            # 删除旧任务
            scheduler.remove_job(instance.job.id)
            instance.delete()

            return Response(
                ScheduledTaskSerializer(new_task).data,
                status=status.HTTP_200_OK
            )

        # 更新元数据
        self.perform_update(serializer)

        if getattr(instance, '_prefetched_objects_cache', None):
            instance._prefetched_objects_cache = {}

        return Response(serializer.data)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        scheduler.remove_job(instance.job.id)
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=['get'])
    def details(self, request, pk=None):
        """任务详情接口"""
        task = self.get_object()
        serializer = self.get_serializer(task)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def run_now(self, request, pk=None):
        """立即执行任务"""
        task = self.get_object()
        job = task.job

        # 获取任务函数
        job_func = job.func_ref

        # 手动执行任务
        try:
            result = job_func(*task.job_args, **task.job_kwargs)
            return Response({
                "status": "success",
                "message": "任务执行成功",
                "result": str(result)
            })
        except Exception as e:
            return Response({
                "status": "error",
                "message": "任务执行失败",
                "exception": str(e)
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=True, methods=['post'])
    def pause(self, request, pk=None):
        """暂停任务"""
        task = self.get_object()
        if task.is_active:
            scheduler.pause_job(task.job.id)
            task.is_active = False
            task.save()
        return Response({"status": "success", "message": "任务已暂停"})

    @action(detail=True, methods=['post'])
    def resume(self, request, pk=None):
        """恢复任务"""
        task = self.get_object()
        if not task.is_active:
            scheduler.resume_job(task.job.id)
            task.is_active = True
            task.save()
        return Response({"status": "success", "message": "任务已恢复"})