from django.db import models


# Create your models here.
class Tag(models.Model):
    id = models.AutoField(primary_key=True)
    tag_uuid = models.CharField(max_length=36)
    tag_name = models.CharField(max_length=36)
    parent = models.CharField(max_length=36, blank=True)
    category = models.CharField(max_length=16, choices=[('VIDEO', '视频'), ('SOUND', '音频'), ('IMAGE', '图像')])
