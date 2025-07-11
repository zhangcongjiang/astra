import uuid

from django.db import models
from django_apscheduler.models import DjangoJob


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
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    job_type = models.CharField(max_length=20, choices=JOB_TYPES)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    job_args = models.JSONField(default=list, blank=True)
    job_kwargs = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.name} ({self.job_type})"

    @property
    def next_run_time(self):
        return self.job.next_run_time

    @property
    def last_execution(self):
        return self.job.executions.order_by('-run_time').first()

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

    @property
    def trigger_config(self):
        if self.job_type == 'interval':
            return f"每 {self.job.interval.seconds} 秒"
        elif self.job_type == 'cron':
            return str(self.job.cron)
        return "一次性任务"

    class Meta:
        verbose_name = "计划任务"
        verbose_name_plural = "计划任务"
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['job_type']),
            models.Index(fields=['is_active']),
            models.Index(fields=['created_at']),
        ]