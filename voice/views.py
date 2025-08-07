import configparser
import hashlib
import json
import logging
import os
import traceback
import uuid
from datetime import datetime
from io import BytesIO

import requests
from django.db.models import Q
from django.utils import timezone
from drf_yasg import openapi
from drf_yasg.utils import swagger_auto_schema
from pydub import AudioSegment
from rest_framework import generics
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from account.models import SystemSettings
from astra.settings import SOUND_PATH, TTS_PATH
from common.response import error_response, ok_response
from tag.models import Tag
from voice.models import Sound, SoundTags, Speaker, SpeakerTags, SpeakerEmotion, Tts
from voice.serializers import SoundSerializer, SpeakerSerializer, TtsSerializer
from voice.text_to_speech import Speech

TIME_FORMAT = '%Y-%m-%dT%H:%M:%S'

logger = logging.getLogger("voice")

conf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sound.ini")
cf = configparser.ConfigParser()
cf.read(conf_path, encoding='utf-8')
DEFAULT_SAMPLE_TEXT = cf.get('default', 'Audio_Sample_Text')


class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'pageSize'
    max_page_size = 1000

    def get_paginated_response(self, data):
        return ok_response(data={
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })


class SoundUploadView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    @swagger_auto_schema(
        operation_description="上传音频特效",
        manual_parameters=[
            openapi.Parameter('file', openapi.IN_FORM, type=openapi.TYPE_FILE, required=True, description="音频文件"),
            openapi.Parameter('name', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True, description="音频名称"),
            openapi.Parameter('singer', openapi.IN_FORM, type=openapi.TYPE_STRING, description="歌手信息"),
            openapi.Parameter('category', openapi.IN_FORM, type=openapi.TYPE_STRING, required=True,
                              enum=['SOUND', 'BGM', 'EFFECT'], default='SOUND',
                              description="音频分类 (SOUND: 普通音频, BGM: 背景音乐, EFFECT: 特效音)")
        ],
        responses={
            201: openapi.Response(description="音频特效上传成功")
        }
    )
    def post(self, request, *args, **kwargs):
        file = request.FILES.get('file')
        name = request.POST.get('name')
        category = request.POST.get('category')
        singer = request.POST.get('singer')
        user = request.user.id

        # 验证必填字段
        if not file:
            return error_response("未提供音频文件")
        if not name:
            return error_response("未提供音频名称")
        if not category:
            return error_response("未提供音频分类")

        # 验证文件格式
        sound_format = file.name.split('.')[-1].lower()
        if sound_format not in ['mp3', 'wav']:
            return error_response("只支持wav、mp3格式音频")

        # 验证分类
        if category not in ['BGM', 'EFFECT', 'SOUND']:
            return error_response("分类必须是 BGM, EFFECT 或 SOUND")

        # 保存文件
        filename = f"{str(uuid.uuid4())}.{sound_format}"
        file_path = os.path.join(SOUND_PATH, filename)

        with open(file_path, 'wb+') as destination:
            for chunk in file.chunks():
                destination.write(chunk)

        # 获取音频时长
        try:
            file.seek(0)
            audio_data = BytesIO(file.read())
            audio = AudioSegment.from_file(audio_data, format=sound_format)
            duration = len(audio) / 1000.0
        except Exception as e:
            return error_response(f"无法解析音频文件: {str(e)}")

        # 创建音频记录
        sound = Sound(
            id=str(uuid.uuid4()),
            name=name,
            singer=singer,
            sound_path=filename,
            spec={
                'duration': round(duration, 2),
                'format': sound_format
            },
            creator=user,
            category=category
        )
        sound.save()

        return ok_response({
            'id': sound.id,
            'name': name,
            'sound_path': sound.sound_path,
            'duration': duration
        })


class SoundListView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SoundSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        start_datetime_str = self.request.query_params.get('start_datetime', '1970-01-01T00:00:00')
        end_datetime_str = self.request.query_params.get('end_datetime', datetime.now().strftime(TIME_FORMAT))
        tag_id = self.request.query_params.get('tag_id', '')
        sort_by = self.request.query_params.get('sort_by', 'create_time')
        order = self.request.query_params.get('order', 'asc')
        category = self.request.query_params.get('category')
        creator = self.request.query_params.get('creator')
        name = self.request.query_params.get('name')
        singer = self.request.query_params.get('singer')
        try:
            start_datetime = timezone.make_aware(datetime.strptime(start_datetime_str, TIME_FORMAT))
            end_datetime = timezone.make_aware(datetime.strptime(end_datetime_str, TIME_FORMAT))
        except ValueError:
            return Sound.objects.none()

        if end_datetime <= start_datetime:
            return Sound.objects.none()

        query = Q()
        if name:
            query &= Q(name__icontains=name)
        if singer:
            query &= Q(singer=singer)
        if creator:
            query &= Q(creator=creator)

        if tag_id:
            try:
                tag = Tag.objects.get(id=tag_id)
                if tag.parent == '':
                    child_tags = Tag.objects.filter(parent=tag).values_list('id', flat=True)
                    sound_ids = SoundTags.objects.filter(tag_id__in=child_tags).values_list('sound_id', flat=True)
                else:
                    sound_ids = SoundTags.objects.filter(tag_id=tag_id).values_list('sound_id', flat=True)
                query &= Q(id__in=sound_ids)
            except Tag.DoesNotExist:
                return Sound.objects.none()
        query &= Q(create_time__range=(start_datetime, end_datetime))
        if category:
            query &= Q(category=category)

        if order == 'desc':
            sort_by = f'-{sort_by}'
        queryset = Sound.objects.filter(query).order_by(sort_by)

        return queryset

    @swagger_auto_schema(
        operation_description="分页查询满足条件的音频文件",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER, default=10),
            openapi.Parameter('start_datetime', openapi.IN_QUERY, description="开始时间 (格式: YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_datetime', openapi.IN_QUERY, description="结束时间 (格式: YYYY-MM-DDTHH:MM:SS)", type=openapi.TYPE_STRING),
            openapi.Parameter('category', openapi.IN_QUERY, description="音频分类 (SOUND: 普通音频, BGM: 背景音乐, EFFECT: 特效音)",
                              type=openapi.TYPE_STRING,
                              default='SOUND'),
            openapi.Parameter('name', openapi.IN_QUERY, description="名称", type=openapi.TYPE_STRING),
            openapi.Parameter('singer', openapi.IN_QUERY, description="歌手", type=openapi.TYPE_STRING),
            openapi.Parameter('tag_id', openapi.IN_QUERY, description="标签ID", type=openapi.TYPE_STRING),
            openapi.Parameter('sort_by', openapi.IN_QUERY, description="排序字段 (默认: create_time)", type=openapi.TYPE_STRING),
            openapi.Parameter('order', openapi.IN_QUERY, description="排序顺序 (asc 或 desc, 默认: asc)", type=openapi.TYPE_STRING),
        ],
        responses={200: SoundSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ok_response(serializer.data)


class DeleteSoundsAPIView(APIView):
    @swagger_auto_schema(
        operation_description="批量删除音频及其关联的标签记录",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sound_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                    description='音频ID列表'
                ),
            },
            required=['sound_ids']
        ),
        responses={
            200: "删除成功",
            400: "无效的输入",
        },
    )
    def post(self, request):
        # 获取请求数据
        sound_ids = request.data.get('sound_ids')

        # 验证输入
        if not sound_ids or not isinstance(sound_ids, list):
            return error_response("输入参数错误，sound_ids必须是一个非空的列表")

        # 批量删除音频及其关联的标签记录
        try:
            # 删除关联的标签记录
            SoundTags.objects.filter(sound_id__in=sound_ids).delete()

            # 删除音频
            sounds = Sound.objects.filter(id__in=sound_ids)
            for sound in sounds:
                if os.path.exists(os.path.join(SOUND_PATH, sound.sound_path)):
                    os.remove(os.path.join(SOUND_PATH, sound.sound_path))
                sound.delete()

            return ok_response("删除成功")

        except Exception as e:
            return error_response(f"删除失败：{str(e)}")


class DeleteSoundTagAPIView(APIView):
    @swagger_auto_schema(
        operation_description="删除音频绑定的单个标签",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sound_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='音频ID'),
                'tag_id': openapi.Schema(type=openapi.TYPE_STRING, format='uuid', description='标签ID'),
            },
            required=['sound_id', 'tag_id']
        ),
        responses={
            200: "删除成功",
            404: "音频或标签绑定关系不存在",
        },
    )
    def post(self, request):
        # 获取请求数据
        sound_id = request.data.get('sound_id')
        tag_id = request.data.get('tag_id')

        if not sound_id or not tag_id:
            return error_response("sound_id 和 tag_id 不能为空")

        try:
            # 查找音频和标签的绑定关系
            sound_tag = SoundTags.objects.get(sound_id=sound_id, tag_id=tag_id)

            # 删除绑定关系
            sound_tag.delete()

            return ok_response("解绑成功")

        except SoundTags.DoesNotExist:
            return error_response("不存在绑定关系")


class SoundDetailView(generics.RetrieveAPIView):
    queryset = Sound.objects.all()
    serializer_class = SoundSerializer
    lookup_field = 'id'  # 根据 UUID 查找音频

    @swagger_auto_schema(
        operation_description="查看音频详情",
        responses={
            200: openapi.Response(
                description="音频详情",
                schema=SoundSerializer
            ),
            404: "音频不存在",
        }
    )
    def get(self, request, *args, **kwargs):
        return self.retrieve(request, *args, **kwargs)


class SpeakerSelectAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="获取所有speaker的id和name供前端选择",
        responses={
            200: openapi.Response(
                description="成功获取speaker选择列表",
                schema=openapi.Schema(
                    type=openapi.TYPE_OBJECT,
                    properties={
                        'data': openapi.Schema(
                            type=openapi.TYPE_ARRAY,
                            items=openapi.Schema(
                                type=openapi.TYPE_OBJECT,
                                properties={
                                    'id': openapi.Schema(type=openapi.TYPE_STRING, description='Speaker ID'),
                                    'name': openapi.Schema(type=openapi.TYPE_STRING, description='Speaker名称')
                                }
                            )
                        )
                    }
                )
            )
        }
    )
    def get(self, request):
        try:
            speakers = Speaker.objects.all().values('id', 'name', 'language', 'emotion', 'speed')
            data = [{'id': str(speaker['id']), 'name': f"{speaker['name']}({speaker['language']}-{speaker['emotion']}-{speaker['speed']})"} for
                    speaker in speakers]
            return ok_response(data)
        except Exception as e:
            logger.error(f"获取speaker选择列表失败: {str(e)}")
            return error_response("获取speaker选择列表失败")


class SpeakerListAPIView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = Speaker.objects.all()
    serializer_class = SpeakerSerializer

    def get_queryset(self):
        name = self.request.query_params.get('name')
        language = self.request.query_params.get('language')
        emotion = self.request.query_params.get('emotion')
        tag_ids = self.request.query_params.getlist('tag_ids')

        query = Q()
        if name:
            query &= Q(name__icontains=name)
        if language:
            query &= Q(language=language)
        if emotion:
            query &= Q(emotion=emotion)

        if tag_ids:
            try:
                speaker_tag_ids = []
                for tag_id in tag_ids:
                    tag = Tag.objects.get(id=tag_id)
                    if tag.parent == '':
                        child_tags = Tag.objects.filter(parent=tag_id).values_list('id', flat=True)
                        speaker_tag_ids.extend(child_tags)
                    else:
                        speaker_tag_ids.append(tag_id)

                speaker_ids = SpeakerTags.objects.filter(tag_id__in=speaker_tag_ids).values_list('speaker_id', flat=True)
                query &= Q(id__in=speaker_ids)
            except Tag.DoesNotExist:
                return Speaker.objects.none()
        queryset = Speaker.objects.filter(query).order_by('-create_time')

        return queryset

    @swagger_auto_schema(
        operation_description="分页查询满足条件的图片",
        manual_parameters=[

            openapi.Parameter('name', openapi.IN_QUERY, description="朗读者名称",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('language', openapi.IN_QUERY, description="语言",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('emotion', openapi.IN_QUERY, description="情感",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('tag_ids', openapi.IN_QUERY,
                              description="标签ID列表（使用tag_ids[]=id1&tag_ids[]=id2的形式传递）",
                              type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_STRING),
                              collection_format='multi')
        ],
        responses={200: SpeakerSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)


class SpeakerListPaginateAPIView(generics.ListAPIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = SpeakerSerializer
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        name = self.request.query_params.get('name')
        language = self.request.query_params.get('language')
        emotion = self.request.query_params.get('emotion')
        tag_ids = self.request.query_params.getlist('tag_ids')

        query = Q()
        if name:
            query &= Q(name__icontains=name)
        if language:
            query &= Q(language=language)
        if emotion:
            query &= Q(emotion=emotion)

        if tag_ids:
            try:
                speaker_tag_ids = []
                for tag_id in tag_ids:
                    tag = Tag.objects.get(id=tag_id)
                    if tag.parent == '':
                        child_tags = Tag.objects.filter(parent=tag_id).values_list('id', flat=True)
                        speaker_tag_ids.extend(child_tags)
                    else:
                        speaker_tag_ids.append(tag_id)

                speaker_ids = SpeakerTags.objects.filter(tag_id__in=speaker_tag_ids).values_list('speaker_id', flat=True)
                query &= Q(id__in=speaker_ids)
            except Tag.DoesNotExist:
                return Speaker.objects.none()
        queryset = Speaker.objects.filter(query).order_by('-create_time')

        return queryset

    @swagger_auto_schema(
        operation_description="分页查询满足条件的图片",
        manual_parameters=[
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页条目数", type=openapi.TYPE_INTEGER,
                              default=10),
            openapi.Parameter('name', openapi.IN_QUERY, description="朗读者名称",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('language', openapi.IN_QUERY, description="语言",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('emotion', openapi.IN_QUERY, description="情感",
                              type=openapi.TYPE_STRING),
            openapi.Parameter('tag_ids', openapi.IN_QUERY,
                              description="标签ID列表（使用tag_ids[]=id1&tag_ids[]=id2的形式传递）",
                              type=openapi.TYPE_ARRAY,
                              items=openapi.Items(type=openapi.TYPE_STRING),
                              collection_format='multi')
        ],
        responses={200: SpeakerSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = self.get_serializer(queryset, many=True)
        return ok_response(serializer.data)


class GenerateSoundAPIView(APIView):
    @swagger_auto_schema(
        operation_description="生成音频接口",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'text': openapi.Schema(type=openapi.TYPE_STRING, description='文本'),
                'speaker_id': openapi.Schema(type=openapi.TYPE_STRING, description='音色'),

            },
            required=['text', 'speaker_id']
        ),
        responses={
            200: "生成成功"
        },
    )
    def post(self, request):
        # 获取请求数据
        text = request.data.get('text')
        speaker_id = request.data.get('speaker_id')

        try:
            Speech().chat_tts(text, speaker_id, request.user.id)
            return ok_response("生成音频成功")

        except Exception:
            return error_response("生成音频失败")


class UpdateSpeakerAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="更新朗读者信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'speaker_id': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    format='uuid',
                    description='朗读者ID'
                ),

                'language': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='语言'
                ),
                'emotion': openapi.Schema(
                    type=openapi.TYPE_STRING,
                    description='情感'
                ),
                'tag_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING, format='uuid'),
                    description='新的标签ID列表'
                ),
                'speed': openapi.Schema(
                    type=openapi.TYPE_NUMBER,
                    description='语速'
                )
            },
            required=['speaker_id']
        ),
        responses={
            200: "更新成功",
            400: "无效的输入",
            404: "朗读者不存在"
        }
    )
    def post(self, request):
        speaker_id = request.data.get('speaker_id')

        language = request.data.get('language')
        emotion = request.data.get('emotion')
        speed = request.data.get('speed')
        tag_ids = request.data.get('tag_ids')

        if not speaker_id:
            return error_response("speaker_id不能为空")

        try:
            # 获取朗读者
            speaker = Speaker.objects.get(id=speaker_id)

            if language:
                speaker.language = language
            if emotion:
                speaker.emotion = emotion
            if speed:
                speaker.speed = speed
            if tag_ids:
                SpeakerTags.objects.filter(speaker_id=speaker_id).delete()
                for tag in tag_ids:
                    SpeakerTags.objects.create(speaker_id=speaker_id, tag_id=tag)

            speaker.save()
            return ok_response("更新成功")

        except Speaker.DoesNotExist:
            return error_response("朗读者不存在")
        except Exception as e:
            return error_response(f"更新失败: {str(e)}")


class SpeakerSampleAudioAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="获取朗读者试听音频",
        manual_parameters=[
            openapi.Parameter('text', openapi.IN_QUERY, description="文本内容", type=openapi.TYPE_STRING),
            openapi.Parameter('is_default', openapi.IN_QUERY, description="是否默认语音", type=openapi.TYPE_BOOLEAN, default=True)
        ],
        responses={
            200: "音频文件",
            404: "朗读者不存在",
            500: "生成试听文件失败"
        }
    )
    def post(self, request):
        try:
            speaker_id = request.data.get('speaker_id')
            text = request.data.get('text')
            is_default = request.data.get('is_default', True)
            if is_default:
                sample_file = os.path.join(TTS_PATH, f'{speaker_id}.wav')
                if os.path.exists(sample_file):
                    return ok_response({"file_path": f"media/tts/{speaker_id}.wav", "sound_id": speaker_id})
                else:
                    sound_id = speaker_id
            else:
                # 根据文本内容和speaker的速度，情感，id算出哈希值，作为文件名，判断如果文件存在，直接返回
                speaker = Speaker.objects.get(id=speaker_id)
                if not speaker:
                    return error_response("朗读者不存在")
                sound_id = uuid.UUID(hashlib.md5(f'{text}{speaker.speed}{speaker.emotion}{speaker_id}'.encode('utf-8')).hexdigest())
                sample_file = os.path.join(TTS_PATH, f'{sound_id}.wav')
                if os.path.exists(sample_file):
                    return ok_response({"file_path": f"media/tts/{sound_id}.wav", "sound_id": sound_id})
            sound = Speech().chat_tts(text, speaker_id, request.user.id, sound_id=sound_id)
            return ok_response({"file_path": f"media/tts/{sound_id}.wav", "sound_id": sound.id})


        except Exception:
            logger.error(f"生成试听文件失败: {traceback.format_exc()}")
            return error_response("生成试听文件失败")


class SpeakerSyncAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="同步音频接口",
        responses={
            200: openapi.Response(
                description="同步成功",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": None,
                        "msg": "同步成功"
                    }
                }
            )
        }
    )
    def post(self, request):
        settings = SystemSettings.objects.filter(user=request.user.id, key='sound').first()
        target_url = settings.value['ttsServerUrl']
        headers = {
            'accept': 'application/json'
        }

        logger.info("开始同步音频标签")

        url = f'{target_url}/models'

        try:
            response = requests.get(url, headers=headers)

            # 检查响应状态码
            if response.status_code == 200:

                models = response.json()
                logger.info(f"音频标签请求成功，响应数据：{models}")
                exist_models = list(Speaker.objects.all().values_list('model', flat=True).distinct())
                new_models = [item for item in models if item not in exist_models]
                delete_models = [item for item in exist_models if item not in models]
                may_update_models = [item for item in exist_models if item in models]
                for model in delete_models:
                    logger.info(f"删除已经不支持的音频类型：{model}")
                    speakers = Speaker.objects.filter(model=model)
                    for speaker in speakers:
                        speaker_id = speaker.id
                        SpeakerEmotion.objects.filter(speaker_id=speaker_id).delete()
                        speaker.delete()
                for model in new_models:
                    logger.info(f"同步新增的音频类型：{model}")
                    headers['Content-Type'] = 'application/json'
                    speakers_response = requests.post(f"{target_url}/spks", headers=headers, data=json.dumps({"model": model}))
                    response_data = speakers_response.json()
                    speakers = response_data.get('speakers', {})

                    for speaker, data in speakers.items():
                        logger.info(f"开始处理speaker{speaker}的数据：{data}")
                        speaker_id = str(uuid.uuid4())
                        Speaker(id=speaker_id, name=speaker, model=model, language=list(data.keys())[0], emotion=list(data.values())[0][0],
                                speed=1.0).save()
                        for language, emotions in data.items():
                            for emotion in emotions:
                                SpeakerEmotion(speaker_id=speaker_id, emotion=emotion, language=language).save()
                for model in may_update_models:
                    headers['Content-Type'] = 'application/json'
                    speakers_response = requests.post(f"{target_url}/spks", headers=headers, data=json.dumps({"model": model}))
                    response_data = speakers_response.json()
                    speakers = response_data.get('speakers', {})
                    exist_speakers = Speaker.objects.filter(model=model)
                    exist_speaker_names = [item.name for item in exist_speakers]
                    for speaker, data in speakers.items():
                        if speaker not in exist_speaker_names:
                            logger.info(f"开始处理speaker{speaker}的数据：{data}")
                            speaker_id = str(uuid.uuid4())
                            Speaker(id=speaker_id, name=speaker, model=model, language=list(data.keys())[0], emotion=list(data.values())[0][0],
                                    speed=1.0).save()
                            for language, emotions in data.items():
                                for emotion in emotions:
                                    SpeakerEmotion(speaker_id=speaker_id, emotion=emotion, language=language).save()
                        else:
                            for item in exist_speakers:
                                if item.name == speaker:
                                    SpeakerEmotion.objects.filter(speaker_id=item.id).delete()
                                    for language, emotions in data.items():
                                        for emotion in emotions:
                                            SpeakerEmotion(speaker_id=item.id, emotion=emotion, language=language).save()

                logger.info(f"同步音频标签完成，本次新增：{new_models}; 删除：{delete_models}")

            else:
                return error_response("文本转音频服务器异常，可能离线了！")

        except requests.exceptions.RequestException as e:
            logger.error(traceback.format_exc())
            return error_response("同步音频出错，请查看后台日志")

        # 这里留空，由你自行实现同步逻辑
        return ok_response("同步成功")


class GetAllLanguagesAPIView(APIView):
    @swagger_auto_schema(
        operation_description="获取所有语言列表",
        responses={
            200: openapi.Response(
                description="语言列表",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": ["中文", "英文"],
                        "msg": "success"
                    }
                }
            )
        }
    )
    def get(self, request):
        languages = SpeakerEmotion.objects.values_list('language', flat=True).distinct()
        return ok_response(list(languages))


class GetLanguagesBySpeakerAPIView(APIView):
    @swagger_auto_schema(
        operation_description="根据朗读者ID获取语言列表",
        manual_parameters=[
            openapi.Parameter('speaker_id', openapi.IN_QUERY, description="朗读者ID", type=openapi.TYPE_STRING, required=True)
        ],
        responses={
            200: openapi.Response(
                description="语言列表",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": ["中文", "英文"],
                        "msg": "success"
                    }
                }
            )
        }
    )
    def get(self, request):
        speaker_id = request.query_params.get('speaker_id')
        if not speaker_id:
            return error_response("speaker_id不能为空")

        languages = SpeakerEmotion.objects.filter(speaker_id=speaker_id).values_list('language', flat=True).distinct()
        return ok_response(list(languages))


class GetAllEmotionsAPIView(APIView):
    @swagger_auto_schema(
        operation_description="获取所有情感列表",
        responses={
            200: openapi.Response(
                description="情感列表",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": ["高兴", "悲伤"],
                        "msg": "success"
                    }
                }
            )
        }
    )
    def get(self, request):
        emotions = SpeakerEmotion.objects.values_list('emotion', flat=True).distinct()
        return ok_response(list(emotions))


class GetEmotionsBySpeakerAPIView(APIView):
    @swagger_auto_schema(
        operation_description="根据朗读者ID获取情感列表",
        manual_parameters=[
            openapi.Parameter('speaker_id', openapi.IN_QUERY, description="朗读者ID", type=openapi.TYPE_STRING, required=True),
            openapi.Parameter('language', openapi.IN_QUERY, description="语言", type=openapi.TYPE_STRING)
        ],
        responses={
            200: openapi.Response(
                description="情感列表",
                examples={
                    "application/json": {
                        "code": 0,
                        "data": ["高兴", "悲伤"],
                        "msg": "success"
                    }
                }
            )
        }
    )
    def get(self, request):
        speaker_id = request.query_params.get('speaker_id')
        language = request.query_params.get('language')

        if not speaker_id:
            return error_response("speaker_id不能为空")

        query = Q(speaker_id=speaker_id)
        if language:
            query &= Q(language=language)

        emotions = SpeakerEmotion.objects.filter(query).values_list('emotion', flat=True).distinct()
        return ok_response(list(emotions))


class SoundPlayView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="播放音频文件",
        manual_parameters=[
            openapi.Parameter('sound_id', openapi.IN_QUERY, type=openapi.TYPE_STRING,
                              required=True, description="音频ID")
        ],
        responses={
            200: openapi.Response(description="音频文件路径",
                                  schema=openapi.Schema(type=openapi.TYPE_OBJECT, properties={
                                      'path': openapi.Schema(type=openapi.TYPE_STRING)
                                  })),
            404: openapi.Response(description="音频不存在或文件未找到")
        }
    )
    def get(self, request):
        sound_id = request.query_params.get('sound_id')
        if not sound_id:
            return error_response("缺少sound_id参数")

        try:
            sound = Sound.objects.get(id=sound_id)
        except Sound.DoesNotExist:
            return error_response("音频不存在")

        # 构建完整文件路径
        file_path = os.path.join(SOUND_PATH, sound.sound_path)

        if not os.path.exists(file_path):
            return error_response("音频文件不存在")
        return ok_response({"file_path": f"media/sound/{sound.sound_path}", "sound_id": sound_id, "format": sound.spec['format']})


class SoundUpdateView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="编辑音频信息",
        request_body=openapi.Schema(
            type=openapi.TYPE_OBJECT,
            properties={
                'sound_id': openapi.Schema(type=openapi.TYPE_STRING, description='音频ID'),
                'name': openapi.Schema(type=openapi.TYPE_STRING, description='音频名称'),
                'singer': openapi.Schema(type=openapi.TYPE_STRING, description='歌手'),
                'tag_ids': openapi.Schema(
                    type=openapi.TYPE_ARRAY,
                    items=openapi.Schema(type=openapi.TYPE_STRING),
                    description='标签ID列表'
                )
            },
            required=['sound_id']
        ),
        responses={
            200: openapi.Response(
                description="编辑成功",
                examples={
                    "application/json": {
                        'code': 0,
                        "message": "音频信息更新成功",
                        "data": {
                            "id": "uuid",
                            "name": "音频名称",
                            "singer": "歌手名称",
                            "tags": []
                        }
                    }
                }
            ),
            400: openapi.Response(
                description="请求参数错误",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "音频ID不能为空",
                        "data": None
                    }
                }
            ),
            404: openapi.Response(
                description="音频不存在",
                examples={
                    "application/json": {
                        'code': 1,
                        "message": "音频不存在",
                        "data": None
                    }
                }
            )
        }
    )
    def post(self, request):
        try:
            sound_id = request.data.get('sound_id')
            if not sound_id:
                return error_response("音频ID不能为空")

            # 查找音频
            try:
                Sound.objects.get(id=sound_id)
            except Sound.DoesNotExist:
                return error_response("音频不存在")
            name = request.data.get('name')
            singer = request.data.get('singer')
            tag_ids = request.data.get('tag_ids')

            Sound.objects.filter(id=sound_id).update(name=name, singer=singer)
            sound_tags = SoundTags.objects.filter(sound_id=sound_id)
            for sg in sound_tags:
                sg.delete()
            for tag in tag_ids:
                SoundTags(sound_id=sound_id, tag_id=tag).save()
            return ok_response("更新成功")

        except Exception as e:
            return error_response(f"更新失败: {str(e)}")


class TtsListAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @swagger_auto_schema(
        operation_description="TTS音频列表查询（支持条件筛选和分页）",
        manual_parameters=[
            openapi.Parameter('video_name', openapi.IN_QUERY, description="视频名称（模糊匹配）", type=openapi.TYPE_STRING),
            openapi.Parameter('speaker_name', openapi.IN_QUERY, description="朗读者名称（模糊匹配）", type=openapi.TYPE_STRING),
            openapi.Parameter('creator', openapi.IN_QUERY, description="创建人（模糊匹配）", type=openapi.TYPE_STRING),
            openapi.Parameter('start_date', openapi.IN_QUERY, description="开始日期(YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('end_date', openapi.IN_QUERY, description="结束日期(YYYY-MM-DD)", type=openapi.TYPE_STRING),
            openapi.Parameter('page', openapi.IN_QUERY, description="页码", type=openapi.TYPE_INTEGER, default=1),
            openapi.Parameter('pageSize', openapi.IN_QUERY, description="每页数量", type=openapi.TYPE_INTEGER, default=20),
        ],
        responses={
            200: TtsSerializer(many=True),
            401: "未授权"
        }
    )
    def get(self, request):
        try:
            # 获取查询参数
            video_name = request.GET.get('video_name', '').strip()
            speaker_name = request.GET.get('speaker_name', '').strip()
            creator = request.GET.get('creator', '').strip()
            start_date = request.GET.get('start_date', '').strip()
            end_date = request.GET.get('end_date', '').strip()

            # 构建查询条件
            query = Q()

            if video_name:
                query &= Q(video_id__icontains=video_name)

            if creator:
                query &= Q(creator__icontains=creator)

            if start_date:
                try:
                    query &= Q(create_time__date__gte=start_date)
                except ValueError:
                    return error_response("开始日期格式错误，请使用YYYY-MM-DD格式")

            if end_date:
                try:
                    query &= Q(create_time__date__lte=end_date)
                except ValueError:
                    return error_response("结束日期格式错误，请使用YYYY-MM-DD格式")

            # 如果有朗读者名称条件，需要先查询Speaker
            if speaker_name:
                speaker_ids = Speaker.objects.filter(name__icontains=speaker_name).values_list('id', flat=True)
                query &= Q(speaker_id__in=speaker_ids)

            # 查询TTS音频列表
            tts_list = Tts.objects.filter(query).order_by('-create_time')

            # 分页处理
            paginator = self.pagination_class()
            page = paginator.paginate_queryset(tts_list, request)

            if page is not None:
                serializer = TtsSerializer(page, many=True)
                return paginator.get_paginated_response(serializer.data)

            serializer = TtsSerializer(tts_list, many=True)
            return ok_response(serializer.data)

        except Exception as e:
            logger.error(f"获取TTS音频列表失败: {str(e)}")
            return error_response("获取TTS音频列表失败")


class TtsPlayAPIView(APIView):
    authentication_classes = [SessionAuthentication, TokenAuthentication]
    permission_classes = [IsAuthenticated]

    @swagger_auto_schema(
        operation_description="试听TTS音频",
        manual_parameters=[
            openapi.Parameter('tts_id', openapi.IN_QUERY, description="TTS音频ID", type=openapi.TYPE_STRING, required=True),
        ],
        responses={
            200: "音频文件路径",
            404: "TTS音频不存在",
            500: "获取音频失败"
        }
    )
    def get(self, request):
        try:
            tts_id = request.GET.get('tts_id')
            if not tts_id:
                return error_response("TTS音频ID不能为空")

            try:
                tts = Tts.objects.get(id=tts_id)
            except Tts.DoesNotExist:
                return error_response("TTS音频不存在")

            # 构建音频文件路径
            audio_file_path = f"media/tts/{tts_id}.wav"

            # 检查文件是否存在
            full_path = os.path.join(TTS_PATH, f'{tts_id}.wav')
            if not os.path.exists(full_path):
                return error_response("音频文件不存在")

            return ok_response({
                "file_path": audio_file_path,
                "tts_id": tts_id,
                "duration": tts.duration,
                "format": tts.format,
                "txt": tts.txt,
                "speaker_id": tts.speaker_id,
                "video_id": tts.video_id,
                "creator": tts.creator,
                "create_time": tts.create_time
            })
        except Exception as e:
            logger.error(f"获取TTS音频失败: {str(e)}")
            return error_response("获取TTS音频失败")
