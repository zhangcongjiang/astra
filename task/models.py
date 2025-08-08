import uuid

from django.db import models
from django_apscheduler.models import DjangoJob, DjangoJobExecution


class ScheduledTask(models.Model):
    JOB_TYPES = (
        ('date', '定时任务'),
        ('interval', '周期性任务'),
        ('manual', '手动任务')
    )

    job = models.OneToOneField(
        DjangoJob,
        on_delete=models.CASCADE,
        related_name='task_metadata',
        blank=True,
        null=True
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    is_active = models.BooleanField(default=True)
    creator = models.CharField(max_length=16)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # 脚本执行相关字段
    script_name = models.CharField(max_length=64, verbose_name='脚本文件名称')
    need_args = models.BooleanField(default=False)

    # 任务调度相关字段
    execution_time = models.DateTimeField(null=True, blank=True, verbose_name='首次执行时间')
    interval = models.DurationField(null=True, blank=True, verbose_name='执行间隔')

    def __str__(self):
        return f"{self.name} ({self.job_type})"

    @property
    def next_run_time(self):
        if self.job:
            return self.job.next_run_time

    @property
    def last_execution(self):
        if self.job:
            job_id = self.job.id
            return DjangoJobExecution.objects.filter(job_id=job_id).order_by('-run_time').first()

    @property
    def last_run_time(self):
        execution = self.last_execution
        return execution.run_time if execution else None

    @property
    def last_run_status(self):
        execution = self.last_execution
        if not execution:
            return "未执行"
        return "成功" if execution.status else "失败"

    class Meta:
        verbose_name = "计划任务"
        verbose_name_plural = "计划任务"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['job_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]
