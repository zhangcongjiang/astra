from django.contrib.auth.models import User
from rest_framework import serializers

from .models import Text


class TextSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()

    class Meta:
        model = Text
        fields = ['id', 'title', 'origin', 'publish', 'creator', 'create_time', 'username']
        read_only_fields = ['id', 'origin', 'create_time']

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class TextDetailSerializer(serializers.ModelSerializer):
    content = serializers.SerializerMethodField()
    username = serializers.SerializerMethodField()

    class Meta:
        model = Text
        fields = ['id', 'title', 'origin', 'publish', 'creator', 'create_time', 'content', 'username']
        read_only_fields = ['id', 'origin', 'create_time']

    def get_content(self, obj):
        """获取文章内容"""
        import os
        from django.conf import settings

        file_path = os.path.join(settings.ARTICLE_PATH, f"{obj.id}.md")
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            return "文章文件不存在"
        except Exception as e:
            return f"读取文章失败: {str(e)}"

    def get_username(self, obj):
        user = User.objects.get(id=obj.creator)
        return user.username


class TextUploadSerializer(serializers.Serializer):
    file = serializers.FileField(help_text="Markdown文件")
    title = serializers.CharField(max_length=36, help_text="文章标题")
    publish = serializers.BooleanField(default=False, help_text="是否发布")

    def validate_file(self, value):
        """验证文件格式"""
        if not value.name.lower().endswith('.md'):
            raise serializers.ValidationError("只支持.md格式的文件")
        return value
