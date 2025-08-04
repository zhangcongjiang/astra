from rest_framework import serializers
from django.contrib.auth.models import User
from django.contrib.auth import authenticate
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


class LoginSerializer(serializers.Serializer):
    """登录序列化器"""
    username = serializers.CharField(max_length=150, required=True, help_text="用户名")
    password = serializers.CharField(max_length=128, required=True, help_text="密码", style={'input_type': 'password'})

    def validate(self, attrs):
        username = attrs.get('username')
        password = attrs.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if not user:
                raise serializers.ValidationError('用户名或密码错误')
            if not user.is_active:
                raise serializers.ValidationError('用户账户已被禁用')
            attrs['user'] = user
        else:
            raise serializers.ValidationError('用户名和密码不能为空')
        
        return attrs




class UserInfoSerializer(serializers.ModelSerializer):
    """用户信息序列化器"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'is_superuser', 'date_joined', 'last_login']
        read_only_fields = ['id', 'username', 'is_superuser', 'date_joined', 'last_login']
