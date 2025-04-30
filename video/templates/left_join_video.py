import logging
import os.path
import uuid

from astra.settings import VIDEO_PATH
from video.templates.video_template import VideoTemplate, InputType, VideoOrientation

logger = logging.getLogger("video")


class NbaHistory(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '模板视频（1）'
        self.desc = '图片翻页生成视频'
        self.parameters = {
            "template_id": {
                "type": InputType.STRING,

            },
            "标题": {
                "type": InputType.TEXT,
                "max": 30,
                "min": 4
            },
            "封面图片": {
                "type": InputType.SELECT,
                "value": "BackgroundImageList"
            },
            "默认音色": {
                "type": InputType.SELECT,
                "value": "SpeakerList"
            },
            "背景音乐": {
                "type": InputType.SELECT,
                "value": "BgmList"
            },
            "开场部分": {
                "type": InputType.OBJECT,
                "value": {
                    '文本': {
                        "type": InputType.TEXT,
                        "max": 0,
                        "min": 0
                    },
                    '媒体数据': {
                        "type": InputType.SELECTLIST,
                        "value": ["NormalImageList", "VideoList"]
                    },
                    "音色": {
                        "type": InputType.SELECT,
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT,
                        "value": "EffectList",
                        "required": False
                    }

                }
            },
            "视频主体": {
                "type": InputType.OBJECTLIST,
                "value": {
                    '转场视频': {
                        "type": InputType.SELECT,
                        "value": "TransitionList",
                        "required": False

                    },
                    '文本': {
                        "type": InputType.TEXT,
                        "max": 0,
                        "min": 0
                    },
                    '媒体数据': {
                        "type": InputType.SELECTLIST,
                        "value": ["NormalImageList", "VideoList"]
                    },
                    "音色": {
                        "type": InputType.SELECT,
                        "value": "SpeakerList",
                        "default": True,
                        "allow_edit": False
                    },
                    "特效音": {
                        "type": InputType.SELECT,
                        "value": "EffectList",
                        "required": False
                    }
                }
            }
        }
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = os.path.join(VIDEO_PATH, f"{self.template_id}.mp4")

    def process(self):
        raise NotImplementedError()

    def calc_start_time(self, total_time, img_num):
        x = round(2 * (total_time - 0.2 * img_num) / (img_num * (img_num + 1)), 2)

        return [0.2 + i * x for i in range(1, img_num + 1)]
