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

    # 脚本执行相关字段
    script_path = models.CharField(max_length=500, verbose_name='脚本文件路径')
    script_args = models.TextField(blank=True, null=True, verbose_name='脚本参数')
    need_args = models.BooleanField(default=False)
    
    # 任务调度相关字段
    run_date = models.DateTimeField(null=True, blank=True, verbose_name='首次执行时间')
    interval = models.DurationField(null=True, blank=True, verbose_name='执行间隔')

    def __str__(self):
        return f"{self.name} ({self.job_type})"

    @property
    def command_line(self):
        """生成完整的命令行"""
        cmd = f"python {self.script_path}"
        if self.script_args and self.script_args.strip():
            cmd += f" {self.script_args.strip()}"
        return cmd

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
