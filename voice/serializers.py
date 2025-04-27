from rest_framework import serializers

from tag.models import Tag
from voice.models import SoundTags, Sound, Speaker, SpeakerTags


class SoundSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Sound
        fields = ['id', 'name', 'desc', 'creator', 'create_time', 'spec', 'sound_path', 'tags']

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


class SoundBindTagsSerializer(serializers.Serializer):
    sound_id = serializers.UUIDField()
    tag_ids = serializers.ListField(child=serializers.UUIDField())


class SpeakerSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Speaker
        fields = ['id', 'name', 'gender', 'sample', 'create_time', 'spec', 'tags']

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
