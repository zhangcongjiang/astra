from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.contrib.auth.models import User
from django.contrib.auth import login, logout
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

from account.models import SystemSettings
from account.serializers import (
    SystemSettingsSerializer, SystemSettingsQuerySerializer, UserListSerializer,
    LoginSerializer, UserInfoSerializer
)
from asset.models import Asset
from common.response import error_response, ok_response
from image.models import Image
from text.models import Text
from video.models import VideoAsset, Parameters
from voice.models import Sound


# Create your views here.
@method_decorator(csrf_exempt, name='dispatch')
class LoginView(APIView):
    """用户登录API"""
    permission_classes = [AllowAny]

    @swagger_auto_schema(
        operation_description="用户登录",
        request_body=LoginSerializer,
        responses={
            200: openapi.Response(
                description="登录成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "message": "登录成功",
                        "data": {
                            "user": {
                                "id": 1,
                                "username": "admin",
                                "email": "admin@example.com",
                                "is_superuser": True
                            },
                            "sessionid": "abc123..."
                        }
                    }
                }
            ),
            400: "登录失败"
        }
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if not serializer.is_valid():
            # 返回详细的错误信息
            error_messages = []
            for field, errors in serializer.errors.items():
                for error in errors:
                    error_messages.append(f"{field}: {error}")
            return error_response("; ".join(error_messages) if error_messages else "输入数据无效")

        user = serializer.validated_data['user']
        login(request, user)

        # 返回用户信息和sessionid
        user_serializer = UserInfoSerializer(user)
        return ok_response(
            data={
                "user": user_serializer.data,
                "sessionid": request.session.session_key
            },
            message="登录成功"
        )


@method_decorator(csrf_exempt, name='dispatch')
class LogoutView(APIView):
    """用户登出API"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="用户登出",
        responses={
            200: "登出成功",
            401: "未登录"
        }
    )
    def post(self, request):
        logout(request)
        return ok_response(message="登出成功")


@method_decorator(csrf_exempt, name='dispatch')
class UserInfoView(APIView):
    """获取当前用户信息API"""
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="获取当前用户信息",
        responses={
            200: UserInfoSerializer,
            401: "未登录"
        }
    )
    def get(self, request):
        serializer = UserInfoSerializer(request.user)
        return ok_response(data=serializer.data, message="获取用户信息成功")


class SystemSettingsAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="系统设置内容更新",
        request_body=SystemSettingsSerializer,
        responses={
            0: "更新成功",
            1: "更新失败",
        },
    )
    def post(self, request):
        # 验证输入数据
        serializer = SystemSettingsSerializer(data=request.data)
        if not serializer.is_valid():
            return error_response("无效的输入")
        user_id = request.user.id
        key = serializer.validated_data['key']
        value = serializer.validated_data['value']
        try:
            settings = SystemSettings.objects.filter(user=user_id, key=key)
            if len(settings) != 1:
                return error_response("系统错误，请联系管理员")
            else:
                setting = settings[0]
                exist_values = setting.value
                for k, v in value:
                    exist_values[k] = v
                setting.value = exist_values
                setting.save()
            return ok_response("更新成功")
        except Exception:
            return error_response("系统错误，请联系管理员")


class SystemSettingsQueryView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="根据key查询系统设置",
        responses={
            0: "查询成功",
            1: "查询失败",
        },
    )
    def get(self, request):
        # 验证输入参数
        serializer = SystemSettingsQuerySerializer(data=request.query_params)
        if not serializer.is_valid():
            return error_response("无效的输入参数")

        user_id = request.user.id
        key = serializer.validated_data['key']

        try:
            # 查询用户的特定配置
            setting = SystemSettings.objects.filter(user=user_id, key=key).first()
            if setting:
                data = {
                    'key': setting.key,
                    'value': setting.value
                }
                return ok_response(data=data, message="查询成功")
            else:
                return error_response("未找到对应的配置项")
        except Exception as e:
            return error_response("系统错误，请联系管理员")


class UserListView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="查询所有用户名",
        responses={
            0: UserListSerializer(many=True),
        },
    )
    def get(self, request):
        """获取所有用户的ID和用户名"""
        try:
            # 查询所有用户，只获取id和username字段
            users = User.objects.all().values('id', 'username', 'is_superuser')

            # 转换为列表格式
            user_list = list(users)

            return ok_response(user_list)
        except Exception as e:
            return error_response("系统错误，请联系管理员")


class CurrentUserView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="查询当前用户信息",
        responses={
            0: "查询成功",
            1: "查询失败",
        },
    )
    def get(self, request):
        """获取所有用户的ID和用户名"""
        try:
            user_id = request.user.id
            # 查询所有用户，只获取id和username字段
            user_basic = User.objects.get(id=user_id)
            user_img_count = Image.objects.filter(creator=user_id).count()
            user_sound_count = Sound.objects.filter(creator=user_id).count()
            user_video_asset_count = VideoAsset.objects.filter(creator=user_id).count()
            user_article_count = Text.objects.filter(creator=user_id).count()
            user_asset_count = Asset.objects.filter(creator=user_id).count()
            user_video_draft_count = Parameters.objects.filter(creator=user_id).count()
            user = {
                "id": user_id,
                "account": user_basic.username,
                "is_superuser": user_basic.is_superuser,
                "username": user_basic.first_name + user_basic.last_name,
                "img_count": user_img_count,
                'sound_count': user_sound_count,
                "article_count": user_article_count,
                "video_asset_count": user_video_asset_count,
                "asset_count": user_asset_count,
                "video_draft_count": user_video_draft_count
            }

            return ok_response(user)
        except Exception as e:
            return error_response("系统错误，请联系管理员")
