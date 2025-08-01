from django.contrib.auth.models import User
from rest_framework import serializers

from tag.models import Tag
from voice.models import SoundTags, Sound, Speaker, SpeakerTags, Tts


class SoundSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Sound
        fields = ['id', 'name', 'desc', 'username', 'singer', 'category', 'create_time', 'spec', 'sound_path', 'tags']

    def get_tags(self, obj):
        # 手动查询 SoundTags 表
        sound_tags = SoundTags.objects.filter(sound_id=obj.id)
        tags = []
        for sound_tag in sound_tags:
            tag = Tag.objects.get(id=sound_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class SpeakerSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()
    class Meta:
        model = Speaker
        fields = ['id', 'name', 'language', 'emotion', 'speed', 'model', 'create_time', 'spec', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
        speaker_tags = SpeakerTags.objects.filter(speaker_id=obj.id)
        tags = []
        for speaker_tag in speaker_tags:
            tag = Tag.objects.get(id=speaker_tag.tag_id)
            tags.append({
                'id': tag.id,
                'tag_name': tag.tag_name,
                'parent': tag.parent,
                'category': tag.category
            })
        return tags


class TtsSerializer(serializers.ModelSerializer):
    speaker_name = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()
    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username

    class Meta:
        model = Tts
        fields = ['id', 'format', 'duration', 'txt', 'speaker_id', 'speaker_name', 'video_id', 'username', 'create_time']

    def get_speaker_name(self, obj):
        try:
            speaker = Speaker.objects.get(id=obj.speaker_id)
            return speaker.name
        except Speaker.DoesNotExist:
            return "未知朗读者"
