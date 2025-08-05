from django.db import models
from django_apscheduler.models import DjangoJob, DjangoJobExecution


class ScheduledTask(models.Model):
    JOB_TYPES = (
        ('date', '一次性'),
        ('interval', '周期性'),
        ('cron', 'Cron表达式')
    )

    job = models.OneToOneField(
        DjangoJob,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name='task_metadata'
    )
    name = models.CharField(max_length=30, unique=True)
    description = models.TextField(blank=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    is_active = models.BooleanField(default=True)
    creator = models.CharField(max_length=16, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    interval_minutes = models.PositiveIntegerField(null=True, blank=True, verbose_name='间隔分钟数')
    interval_hours = models.PositiveIntegerField(null=True, blank=True, verbose_name='间隔小时数')
    interval_days = models.PositiveIntegerField(null=True, blank=True, verbose_name='间隔天数')

    spec = models.JSONField(default=list, blank=True)
    def __str__(self):
        return f"{self.name} ({self.job_type})"

    @property
    def next_run_time(self):
        return self.job.next_run_time

    @property
    def last_execution(self):
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