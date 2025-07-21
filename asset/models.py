import uuid

from django.db import models


# Create your models here.
class Asset(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    set_name = models.CharField(max_length=30)
    creator = models.CharField(max_length=36, blank=True)
    create_time = models.DateTimeField(auto_now_add=True)


class AssetInfo(models.Model):
    ASSET_CHOICES = [
        ('image', '图片'),
        ('video', '视频'),
        ('sound', '音频'),
        ('text', '文本'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    set_id = models.CharField(max_length=36)
    resource_id = models.CharField(max_length=36)
    asset_type = models.CharField(max_length=16, choices=ASSET_CHOICES)
    index = models.PositiveIntegerField(db_index=True)
    
    def save(self, *args, **kwargs):
        if not self.index:
            # 获取当前set_id下最大的index值，如果没有记录则从0开始
            max_index = AssetInfo.objects.filter(set_id=self.set_id).aggregate(
                models.Max('index')
            )['index__max'] or 0
            self.index = max_index + 1
        super().save(*args, **kwargs)
    
    class Meta:
        ordering = ['set_id', 'index']
        # 确保在同一个set_id内index是唯一的
        unique_together = [['set_id', 'index']]
