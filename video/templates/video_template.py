import glob
import json
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from enum import Enum

from proglog import ProgressBarLogger
from pydub import AudioSegment

from astra import settings
from astra.settings import FONTS_PATH, SOUND_PATH, VIDEO_PATH, IMG_PATH, FFMPEG_PATH, BGM_PATH
from common.exceptions import BusinessException
from common.redis_tools import ControlRedis
from common.text_utils import TextUtils
from video.models import Parameters

logger = logging.getLogger("video")


class VideoOrientation(Enum):
    HORIZONTAL = 0  # 横版视频
    VERTICAL = 1  # 竖版视频


class InputType(Enum):
    STRING = 0
    TEXT = 1
    OBJECT = 2
    CHOICE = 3  # 下拉选项
    SELECT = 4  # 选择选项
    OBJECT_LIST = 5
    SELECT_LIST = 6


class VideoTemplate:
    def __init__(self):
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.ffmpeg_path = FFMPEG_PATH
        self.img_path = IMG_PATH
        self.sound_path = SOUND_PATH
        self.movie_path = VIDEO_PATH
        self.bgm_path = BGM_PATH
        self.font = os.path.join(FONTS_PATH, 'STXINWEI.TTF')
        self.name = ''
        self.desc = ''
        self.frame_rate = 20
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.parameters = {}
        self.demo = None
        self.templates = []
        self.methods = {}
        self.clips = []
        self.audio_clips = []
        self.subtitle_clips = []
        self.executor = ThreadPoolExecutor(max_workers=8)
        self.set_ffmpeg_path()
        self.text_utils = TextUtils()
        # redis 记录视频生成进度
        self.redis_control = ControlRedis()

    def set_ffmpeg_path(self):
        os.environ["PATH"] += os.pathsep + os.path.dirname(self.ffmpeg_path)
        AudioSegment.converter = self.ffmpeg_path

    def generate_video(self, parameters):
        template_id = parameters.get('template_id')
        if template_id not in self.methods.keys():
            return 'Method not found'
        video_id = str(uuid.uuid4())
        logger.info("生成视频封面完成")
        self.executor.submit(self.methods[template_id]().process, video_id, parameters)
        return {
            'video_id': video_id,
            'parameters': parameters
        }

    def get_templates(self):
        subclasses = VideoTemplate.__subclasses__()
        for subclass in subclasses:
            # 创建子类实例
            instance = subclass()
            if instance.template_id not in self.methods.keys():
                template_info = {
                    "template_id": instance.template_id,
                    "name": instance.name,
                    "desc": instance.desc,
                    "parameters": instance.parameters,
                    "orientation": instance.orientation,
                    "demo": instance.demo
                }
                self.templates.append(template_info)
                logger.info(f"register {instance.name}，info: {template_info}")
                self.methods[instance.template_id] = subclass
        return self.templates

    @staticmethod
    def download(video_id):
        from video.models import Video
        video = Video.objects.get(video_id=video_id)
        if not video.result:
            logger.error("视频生成失败，请重新生成")
            raise BusinessException("视频生成失败，请重新生成")
        else:
            video_filename = f'{video_id}.mp4'
            video_path = os.path.join(settings.VIDEO_PATH, video_filename)

            # 直接返回视频文件的路径或文件对象
            logger.info(f"视频{video_id}下载成功")
            return video_path

    def clear_temps(self, video_id):
        # 构建搜索模式
        search_pattern = os.path.join(self.sound_path, f"{video_id}*")

        # 获取所有匹配的文件
        files_to_delete = glob.glob(search_pattern)

        # 删除每个文件
        for file_path in files_to_delete:
            try:
                os.remove(file_path)
            except Exception as e:
                print(f"Failed to delete {file_path}: {e}")
        print("临时音频文件删除完成")

    @staticmethod
    def save_parameters(data):
        param_id = str(uuid.uuid4())
        Parameters(id=param_id, data=data).save()
        return param_id

    @staticmethod
    def get_size(orientation):
        if orientation == VideoOrientation.HORIZONTAL.name:
            return 1600, 900
        elif orientation == VideoOrientation.VERTICAL.name:
            return 900, 1600
        else:
            logger.error(f"视频类型异常，{orientation}")


class MyBarLogger(ProgressBarLogger):
    def __init__(self, video_id):
        super().__init__()
        self.video_id = video_id
        self.redis = ControlRedis()

    def bars_callback(self, bar, attr, value, old_value=None):
        # Every time the logger progress is updated, this function is called
        percentage = (value / self.bars[bar]['total']) * 100
        self.redis.set_key(self.video_id, round(percentage, 2))
