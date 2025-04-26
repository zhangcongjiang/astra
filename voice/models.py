import uuid

from django.db import models


# Create your models here.

class Sound(models.Model):
    CATEGORY_CHOICES = [
        ('BGM', '背景音乐'),
        ('EFFECT', '特效音'),
        ('SOUND', '普通音频'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_path = models.TextField()
    name = models.CharField(blank=True)
    desc = models.TextField()
    category = models.CharField(blank=False, choices=CATEGORY_CHOICES, default='SOUND')
    creator = models.CharField(max_length=36)
    create_time = models.DateTimeField(auto_now_add=True)  # 时间
    spec = models.JSONField(default=dict, null=True, blank=True)


class Speaker(models.Model):
    GENDER_CHOICES = [
        ('MALE', '男'),
        ('FEMALE', '女'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField()
    voice_style = models.CharField(max_length=36)  # 保存重命名后的音色种子文件名
    gender = models.CharField(max_length=6, choices=GENDER_CHOICES, blank=False)
    spec = models.JSONField(default=dict, null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # 如果有音色种子文件需要处理
        if hasattr(self, '_voice_style_file'):
            # 生成新的文件名
            new_filename = f"{uuid.uuid4()}.pt"
            # TODO: 调用外部接口保存文件
            # 这里应该调用外部接口将self._voice_style_file保存为new_filename
            # 暂时模拟保存成功
            self.voice_style = new_filename
        super().save(*args, **kwargs)


class SoundTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sound_id = models.UUIDField()
    tag_id = models.UUIDField()

class SpeakerTags(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    speaker_id = models.UUIDField()
    tag_id = models.UUIDField()
