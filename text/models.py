import uuid

from django.db import models


# Create your models here.
class Text(models.Model):
    '''图文'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=30, blank=False)
    cover_id = models.CharField(null=True, max_length=36, blank=True, verbose_name='视频封面')
    publish = models.BooleanField(default=False)
    creator = models.CharField(max_length=36, blank=False)
    origin = models.CharField(max_length=36, default="用户创建")
    create_time = models.DateTimeField(auto_now_add=True)  # 时间


class Graph(models.Model):
    '''素材里的文本片段'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    text = models.TextField()
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间


class Dynamic(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=30, blank=True, null=True)
    content = models.TextField(blank=False)
    publish = models.BooleanField(default=False)
    creator = models.CharField(max_length=36, blank=False)
    origin = models.CharField(max_length=36, default="用户创建")
    create_time = models.DateTimeField(auto_now_add=True)  # 时间


class DynamicImage(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dynamic_id = models.CharField(null=True, max_length=36, blank=True, verbose_name='动态ID')
    image_id = models.CharField(null=True, max_length=36, blank=True, verbose_name='图像ID')
    index = models.PositiveIntegerField(db_index=True)

    def save(self, *args, **kwargs):
        if self.index is None:
            # 在同一个 dynamic_id 下计算当前最大的 index，然后递增
            max_index = DynamicImage.objects.filter(dynamic_id=self.dynamic_id).aggregate(
                models.Max('index')
            )['index__max'] or 0
            self.index = max_index + 1
        super().save(*args, **kwargs)

    class Meta:
        ordering = ['dynamic_id', 'index']
        # 确保在同一个 dynamic_id 内 index 是唯一的
        unique_together = [['dynamic_id', 'index']]
