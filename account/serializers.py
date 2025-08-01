from rest_framework import serializers

from django.contrib.auth.models import User

from account.models import SystemSettings


class SystemSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemSettings
        fields = ['key', 'value']


class SystemSettingsQuerySerializer(serializers.Serializer):
    key = serializers.CharField(max_length=36, required=True, help_text="配置项的键")


class UserListSerializer(serializers.ModelSerializer):
    """用户列表序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username']
        read_only_fields = ['id', 'username']
