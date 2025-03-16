from rest_framework import serializers

from tag.models import Tag
from voice.models import SoundTags, Sound


class SoundSerializer(serializers.ModelSerializer):
    tags = serializers.SerializerMethodField()

    class Meta:
        model = Sound
        fields = ['id', 'name', 'desc', 'height', 'creator', 'create_time', 'spec', 'effect_path', 'tags']

    def get_tags(self, obj):
        # 手动查询 ImageTags 表
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
