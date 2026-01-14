import logging
import os
import shutil
import time
import traceback
import uuid

import numpy as np
from PIL import Image as PilImage, ImageDraw, ImageFont, ImageEnhance
from moviepy import *
from moviepy.audio.fx import AudioFadeOut
from pydub import AudioSegment

from astra.settings import VIDEO_PATH, LOGO_PATH, IMG_PATH, TMP_PATH
from image.models import Image
from video.models import Video
from video.video_templates.video_template import VideoTemplate, VideoOrientation
from voice.models import Sound

logger = logging.getLogger("video")

title_font = ImageFont.truetype('STXINWEI.TTF', 40)
name_font = ImageFont.truetype('STXINWEI.TTF', 36)
data_font = ImageFont.truetype('STXINWEI.TTF', 30)
background_color = '#ffffff'


class PlayerCompare(VideoTemplate):

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '数据对比生成视频'
        self.desc = '通过两组数据对比，结合背景音乐和部分图片，生成视频'
        self.parameters = {
            'form': [

                {
                    'name': 'title',
                    'label': '视频标题',
                    'type': 'input',
                    'inputType': 'text',
                    'required': True,
                    'placeholder': '请输入视频的标题'
                },
                {
                    'name': 'reader',
                    'label': '选择配音员',
                    'type': 'select',
                    'required': False,
                    'options': {
                        'source': 'remote',
                        'url': '/voice/speakers/select/',
                        'valueKey': 'id',
                        'labelKey': 'name'
                    },
                    'description': '选择一个AI配音员来朗读文案。'
                },
                {
                    'name': 'bgm',
                    'label': '背景音乐',
                    'type': 'select',
                    'required': True,
                    'options': {
                        'source': 'server',
                        'resourceType': 'audio'
                    },
                    'description': '从您的媒体库中选择一首背景音乐。'
                },
                {
                    'name': 'start_text',
                    'label': '开场文案',
                    'type': 'textarea',
                    'rows': 3,
                    'required': True,
                    'placeholder': '请输入视频的开场白。'
                },
                {
                    'name': 'main',
                    'label': '主要比较者',
                    'type': 'group',
                    'replicable': False,
                    'fields': [{
                        'name': 'avatar',
                        'label': '头像',
                        'type': 'select',
                        'multiple': False,
                        'required': True,
                        'options': {
                            'source': 'server',
                            'resourceType': 'image'
                        }

                    },
                        {
                            'name': 'body',
                            'label': '全身照',
                            'type': 'select',
                            'multiple': False,
                            'required': True,
                            'options': {
                                'source': 'server',
                                'resourceType': 'image'
                            }
                        },
                        {
                            'name': 'name',
                            'label': '姓名',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入主要比较者名称。'
                        },
                        {
                            'name': 'draft',
                            'label': '选秀顺位',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入选秀顺位。'
                        },
                        {
                            'name': 'game_result',
                            'label': '战绩',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入战绩。'
                        },
                        {
                            'name': 'data',
                            'label': '数据',
                            'type': 'textarea',
                            'rows': 3,
                            'required': True,
                            'placeholder': '请输入数据。'
                        }
                    ]
                },
                {
                    'name': 'compared',
                    'label': '被比较者',
                    'type': 'group',
                    'replicable': False,
                    'fields': [{
                        'name': 'avatar',
                        'label': '头像',
                        'type': 'select',
                        'multiple': False,
                        'required': True,
                        'options': {
                            'source': 'server',
                            'resourceType': 'image'
                        }

                    },
                        {
                            'name': 'body',
                            'label': '全身照',
                            'type': 'select',
                            'multiple': False,
                            'required': True,
                            'options': {
                                'source': 'server',
                                'resourceType': 'image'
                            }
                        },
                        {
                            'name': 'name',
                            'label': '姓名',
                            'type': 'textarea',
                            'rows': 1,
                            'required': True,
                            'placeholder': '请输入被比较者名称。'
                        },
                        {
                            'name': 'draft',
                            'label': '选秀顺位',
                            'type': 'textarea',
                            'rows': 1,
                            'required': True,
                            'placeholder': '请输入选秀顺位。'
                        },
                        {
                            'name': 'game_result',
                            'label': '战绩',
                            'type': 'textarea',
                            'rows': 1,
                            'required': True,
                            'placeholder': '请输入战绩。'
                        },
                        {
                            'name': 'key_note',
                            'label': '关键信息',
                            'type': 'textarea',
                            'rows': 1,
                            'required': True,
                            'placeholder': '请输入关键信息。'
                        },
                        {
                            'name': 'data',
                            'label': '数据',
                            'type': 'textarea',
                            'rows': 1,
                            'required': True,
                            'placeholder': '请输入数据。'
                        }
                    ]
                },
                {
                    'name': 'copywriting',
                    'label': '文案内容',
                    'type': 'textarea',
                    'rows': 3,
                    'required': False,
                    'placeholder': '请输入视频文案。'
                }
            ]
        }
        self.orientation = VideoOrientation.VERTICAL.name
        self.demo = "/media/videos/player_compare.mp4"
        self.default_speaker = None
        self.width, self.height = self.get_size(self.orientation)
        self.duration_start = 0
        self.cover = None
        self.video_type = 'Regular'
        self.tmps = None

    def process(self, user, video_id, parameters):
        """实现带字幕和音频同步的视频生成

        Args:
            video_id: 视频唯一ID
            parameters: 包含图片路径列表和文本的参数
            :param user: 创建者
        """

        begin = time.time()  # 记录开始时间

        self.tmps = os.path.join(TMP_PATH, video_id)
        if not os.path.exists(self.tmps):
            os.mkdir(self.tmps)
        logger.info(f"视频生成请求参数：{parameters}")
        project_name = parameters.get('title')
        param_id = self.save_parameters(self.template_id, user, project_name, parameters)

        # 获取开场部分和视频主体内容
        start_text = parameters.get('start_text', '').replace('·', '')

        bgm = parameters.get('bgm')  # 获取背景音乐路径
        copywriting = parameters.get('copywriting')
        main_data = parameters.get('main', {})
        compared_data = parameters.get('compared', {})
        main_avatar_path = main_data['avatar']
        compared_avatar_path = compared_data['avatar']
        main_body_path = main_data['body']
        compared_body_path = compared_data['body']

        resized_main_avatar_path = os.path.join(self.tmps, 'resized_main_avatar.png')
        avatar_img = PilImage.open(main_avatar_path)
        resized_img = self.img_utils.resize_and_crop(avatar_img, 390, 255)
        resized_img.save(resized_main_avatar_path)

        resized_compared_avatar_path = os.path.join(self.tmps, 'resized_compared_avatar.png')
        avatar_img = PilImage.open(compared_avatar_path)
        resized_img = self.img_utils.resize_and_crop(avatar_img, 390, 255)
        resized_img.save(resized_compared_avatar_path)

        trim_main_body_path = os.path.join(self.tmps, 'trim_main_body.png')

        self.resize_body(main_body_path, trim_main_body_path)

        trim_compared_body_path = os.path.join(self.tmps, 'trim_compared_body.png')

        self.resize_body(compared_body_path, trim_compared_body_path)

        output_path = os.path.join(VIDEO_PATH, f"{video_id}.mp4")

        reader = parameters.get('reader')
        self.default_speaker = reader

        Video(creator=user, title=f"{main_data.get('name').split('·')[-1]}vs{compared_data.get('name').split('·')[-1]}{project_name}",
              content=copywriting + "\n\n", video_type=self.video_type,
              result='Process',
              process=0.0, id=video_id, param_id=param_id).save()
        try:
            vertical_cover = self.generate_vertical_cover(project_name, main_data.get('name'), compared_data.get('name'), trim_main_body_path,
                                                          trim_compared_body_path, user)
            Video.objects.filter(id=video_id).update(vertical_cover=vertical_cover)

            horizontal_cover = self.generate_horizontal_cover(main_data.get('name'), compared_data.get('name'), trim_main_body_path,
                                                              trim_compared_body_path, user)
            Video.objects.filter(id=video_id).update(cover=horizontal_cover)

            _cover = Image.objects.get(id=vertical_cover)
            cover_img_path = os.path.join(self.img_path, _cover.img_name)
            segments = self.text_utils.split_text(start_text)

            subtitlers = []
            start = 0.5
            final_audio = AudioSegment.silent(duration=0)

            for i, sg in enumerate(segments):
                tts = self.speech.chat_tts(sg, reader, user, video_id)
                tts_path = os.path.join(self.tts_path, f'{tts.id}.{tts.format}')
                audio = AudioSegment.from_file(tts_path).fade_in(200).fade_out(200)
                for text_clip in self.subtitler.text_clip(sg, start, tts.duration, 1310, self.width):
                    subtitlers.append(text_clip)
                if i == 0:
                    final_audio = audio
                    start += tts.duration
                else:
                    final_audio = final_audio.append(audio, crossfade=200)
                    start += tts.duration - 0.2
            audio_path = os.path.join(self.tmps, "merged_tts.mp3")
            final_audio.export(audio_path, format="mp3")

            Video.objects.filter(id=video_id).update(process=0.2)

            data = {
                "main": {
                    "name": main_data.get('name'),
                    "draft": main_data.get('draft'),
                    "key_note": main_data.get('key_note'),
                    "game_result": main_data.get('game_result'),
                    "data": main_data.get('data'),
                    "season": main_data.get('season')
                },
                "compared": {
                    "name": compared_data.get('name'),
                    "draft": compared_data.get('draft'),
                    "key_note": compared_data.get('key_note'),
                    "game_result": compared_data.get('game_result'),
                    "data": compared_data.get('data'),
                    "season": compared_data.get('season')
                }

            }
            bgm_sound = Sound.objects.get(id=bgm)
            self.create_video_with_effects(project_name,
                                           resized_main_avatar_path, resized_compared_avatar_path,
                                           trim_main_body_path, trim_compared_body_path,
                                           cover_img_path,
                                           output_path, data,
                                           audio_path,  # 开场音频文件
                                           subtitlers,
                                           os.path.join(self.sound_path, bgm_sound.sound_path)  # 背景音乐路径
                                           )
            # 获取生成的视频文件大小
            video_size = 0
            if os.path.exists(output_path):
                video_size = os.path.getsize(output_path)

            Video.objects.filter(id=video_id).update(result='Success', process=1.0, video_path=f"/media/videos/{video_id}.mp4",
                                                     cost=time.time() - begin, size=video_size)
        except Exception as e:
            logger.error(traceback.format_exc())
            Video.objects.filter(id=video_id).update(result='Fail')
            if os.path.exists(output_path):
                os.remove(output_path)
            raise e
        finally:
            if os.path.exists(self.tmps):
                shutil.rmtree(self.tmps)

    def resize_body(self, image_path, save_path, max_width=350, max_height=600):
        img = self.img_utils.trim_image(image_path)
        w, h = img.size

        # 如果在限制范围内，直接保存
        if w <= max_width and h <= max_height:
            img.save(save_path)
            return

        # 计算缩放比例（取最小的，保证都不超）
        scale = min(max_width / w, max_height / h)

        new_w = int(w * scale)
        new_h = int(h * scale)

        resized_img = img.resize((new_w, new_h), PilImage.LANCZOS)
        resized_img.save(save_path)

    def create_deal_animation(self, img_path, final_position, start_time, duration, total_duration):
        """
        创建类似“发牌”的动画：图片从右上角快速飞到指定位置
        """
        # 使用PIL加载并调整图片尺寸
        pil_img = PilImage.open(img_path).convert("RGBA")

        # 转为 numpy 数组并创建 ImageClip
        img_array = np.array(pil_img)
        img = ImageClip(img_array).with_duration(total_duration)

        # 起始位置（右上角飞入）
        start_pos = (900, -img.h)

        # 位置动画
        def position_func(t):
            if t < start_time:  # 还没开始飞
                return start_pos
            elif start_time <= t < start_time + duration:
                linear_progress = (t - start_time) / duration
                progress = 1 - (1 - linear_progress) ** 2  # ease-out
                x = start_pos[0] + (final_position[0] - start_pos[0]) * progress
                y = start_pos[1] + (final_position[1] - start_pos[1]) * progress
                return (x, y)
            else:  # 到达目标位置
                return final_position

        return img.with_position(position_func)

    def create_name_typewriter_effect(self, data, start_time, total_duration):
        """
        创建球员姓名打字机效果
        """

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 只在开始时间后才显示
            if t >= start_time:
                main = data.get('main')
                compared = data.get('compared')

                # 计算当前应该显示的文字长度
                progress = min(1, (t - start_time) / 1)  # 名字打字效果持续1秒（你可以调整）

                # 主球员名字打字效果
                main_name = main.get('name')
                main_chars_to_show = int(len(main_name) * progress)
                current_main_text = main_name[:main_chars_to_show]
                main_mask = name_font.getmask(current_main_text)
                draw.text((225 - int(main_mask.size[0]) / 2, 315), text=current_main_text, font=name_font, fill=(255, 60, 60))

                # 对比球员名字打字效果
                compared_name = compared.get('name')
                compared_chars_to_show = int(len(compared_name) * progress)
                current_compared_text = compared_name[:compared_chars_to_show]
                compared_mask = name_font.getmask(current_compared_text)
                draw.text((675 - int(compared_mask.size[0]) / 2, 315), text=current_compared_text, font=name_font, fill='yellow')

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建打字机效果，并在完成后保持显示
    def create_typewriter_effect(self, text, position, duration, total_duration, bg_points=None):
        """
        创建打字机效果，并在完成后保持显示
        """

        # 创建临时函数来生成每一帧
        def make_frame(t):
            # 创建新的图像
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 绘制梯形背景（如果提供了背景点）
            if bg_points:
                draw.polygon(bg_points, fill="#66666")

            # 计算当前应该显示的文字长度
            if t < duration:
                progress = min(1, t / duration)
                chars_to_show = int(len(text) * progress)
                current_text = text[:chars_to_show]
            else:
                current_text = text  # 动画完成后显示完整文字

            # 绘制文字

            draw.text(position, current_text, font=title_font, fill="gold")

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建静态梯形背景
    def create_static_background(self, bg_points, total_duration, title_y, hex_height):
        """
        创建静态梯形背景
        """

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.line([(30, title_y + hex_height / 2), (870, title_y + hex_height / 2)], fill=background_color, width=2)
            draw.polygon(bg_points, fill="#333333")
            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 创建球员信息显示效果（在所有图片到达后显示）
    def create_player_info_effect(self, data, start_time, total_duration):
        """
        创建球员信息显示效果
        """

        background_color = '#ffffff'

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)

            # 只在开始时间后才显示
            if t >= start_time:
                main = data.get('main')
                compared = data.get('compared')

                if main.get('name') != compared.get('name'):
                    # 绘制选秀信息
                    main_draft = main.get('draft')
                    compared_draft = compared.get('draft')
                    draw.text((225 - int(data_font.getmask(main_draft).size[0]) / 2, 359), text=main_draft, font=data_font, fill=background_color)
                    draw.text((675 - int(data_font.getmask(compared_draft).size[0]) / 2, 359), text=compared_draft, font=data_font,
                              fill=background_color)
                else:
                    main_season = f"{main.get('season')}赛季"
                    compared_season = f"{compared.get('season')}赛季"
                    draw.text((225 - int(data_font.getmask(main_season).size[0]) / 2, 359), text=main_season, font=data_font, fill=background_color)
                    draw.text((675 - int(data_font.getmask(compared_season).size[0]) / 2, 359), text=compared_season, font=data_font,
                              fill=background_color)

                main_key_note = main.get('key_note')
                compared_key_note = compared.get('key_note')
                draw.text((225 - int(data_font.getmask(main_key_note).size[0]) / 2, 398), text=main_key_note, font=data_font, fill=background_color)
                draw.text((675 - int(data_font.getmask(compared_key_note).size[0]) / 2, 398), text=compared_key_note, font=data_font,
                          fill=background_color)

                # 绘制比赛结果
                main_game_result = main.get('game_result')
                compared_game_result = compared.get('game_result')
                draw.text((225 - int(name_font.getmask(main_game_result).size[0]) / 2, 437), text=main_game_result, font=name_font,
                          fill=(255, 60, 60))
                draw.text((675 - int(name_font.getmask(compared_game_result).size[0]) / 2, 437), text=compared_game_result, font=name_font,
                          fill='yellow')

            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    def create_data_bar_effect(self, data, start_time, total_duration):
        """
        仅绘制数据对比的进度条与（弱化的）槽边框，用于放在 body 照片下层。
        """
        # 颜色（弱化透明度）

        reverse_items = ['失误']
        left_base_light = (128, 0, 0, 128)
        left_base_dark = (255, 0, 0, 192)
        right_base_light = (255, 255, 128, 128)
        right_base_dark = (255, 255, 0, 192)
        slot_outline_color = (255, 255, 255, 96)

        # 数据槽位置参数
        bar_y_start = 600
        bar_height = 40
        bar_spacing = 60
        left_bar_x1, left_bar_x2 = 60, 380
        right_bar_x1, right_bar_x2 = 520, 840
        left_total = left_bar_x2 - left_bar_x1
        right_total = right_bar_x2 - right_bar_x1

        main_data = data['main']['data']
        compared_data = data['compared']['data']
        data_items = list(main_data.keys())

        def lerp_color(c1, c2, p):
            return tuple(int(c1[i] + (c2[i] - c1[i]) * p) for i in range(4))

        def draw_left_bar(img, bar_y, fill_w, color):
            if fill_w <= 0:
                return
            # 从左侧边界向中间推进
            layer = PilImage.new('RGBA', (fill_w, bar_height), color)
            img.paste(layer, (left_bar_x1, bar_y), layer)

        def draw_right_bar(img, bar_y, fill_w, color):
            if fill_w <= 0:
                return
            # 从右侧边界向中间推进
            layer = PilImage.new('RGBA', (fill_w, bar_height), color)
            img.paste(layer, (right_bar_x2 - fill_w, bar_y), layer)

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            if t >= start_time:
                elapsed_time = t - start_time
                for i, item in enumerate(data_items):
                    bar_y = bar_y_start + i * bar_spacing
                    item_start_time = i * 2.5
                    if elapsed_time < item_start_time:
                        continue
                    progress = min(1, (elapsed_time - item_start_time) / 2.5)
                    # 边框（弱化）
                    draw.rectangle([left_bar_x1, bar_y, left_bar_x2, bar_y + bar_height], outline=slot_outline_color, width=1)
                    draw.rectangle([right_bar_x1, bar_y, right_bar_x2, bar_y + bar_height], outline=slot_outline_color, width=1)
                    main_value = main_data[item]
                    compared_value = compared_data[item]

                    if item not in reverse_items:

                        if main_value == compared_value:
                            left_target = left_total
                            right_target = right_total
                        elif main_value > compared_value:
                            left_target = left_total
                            right_target = int(right_total * (compared_value / main_value)) if main_value != 0 else 0
                        else:
                            right_target = right_total
                            left_target = int(left_total * (main_value / compared_value)) if compared_value != 0 else 0
                    else:
                        if main_value == compared_value:
                            left_target = left_total
                            right_target = right_total
                        elif main_value > compared_value:
                            left_target = int(right_total * (compared_value / main_value)) if main_value != 0 else 0
                            right_target = left_total
                        else:
                            right_target = int(left_total * (main_value / compared_value)) if compared_value != 0 else 0
                            left_target = right_total
                    left_current = int(left_target * progress)
                    right_current = int(right_target * progress)
                    left_bar_color = lerp_color(left_base_light, left_base_dark, progress)
                    right_bar_color = lerp_color(right_base_light, right_base_dark, progress)
                    draw_left_bar(img, bar_y, left_current, left_bar_color)
                    draw_right_bar(img, bar_y, right_current, right_bar_color)
            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    def create_data_text_effect(self, data, start_time, total_duration):
        """
        仅绘制数据对比的文字（类别标签与左右数值），用于放在 body 照片上层。
        """
        background_color = '#ffffff'
        bar_y_start = 600
        bar_height = 40
        bar_spacing = 60
        left_bar_x1, left_bar_x2 = 60, 380
        right_bar_x1, right_bar_x2 = 520, 840
        main_data = data['main']['data']
        compared_data = data['compared']['data']
        data_items = list(main_data.keys())
        percent_items = ['投篮', '三分球', '罚球', '胜率', '真实命中']
        int_items = ['出战场次']

        def fmt_value(item, v):
            if item in percent_items:
                return f"{round(v, 1)}%" if isinstance(v, float) else f"{v}%"
            elif item in int_items:
                return f"{int(v)}"
            else:
                return f"{round(v, 1)}" if isinstance(v, float) else f"{v}"

        def make_frame(t):
            img = PilImage.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            if t >= start_time:
                elapsed_time = t - start_time
                for i, item in enumerate(data_items):
                    bar_y = bar_y_start + i * bar_spacing
                    item_start_time = i * 2.5
                    if elapsed_time < item_start_time:
                        continue
                    progress = min(1, (elapsed_time - item_start_time) / 2.5)
                    # 类型文字颜色：动画中红色，结束后白色
                    label_color = (255, 60, 60, 255) if progress < 1 else background_color
                    label_width = data_font.getmask(item).size[0]
                    label_x = 450 - label_width / 2
                    draw.text((label_x, bar_y + (bar_height - 24) // 2), text=item, font=data_font, fill=label_color)
                    # 数值随进度变化

                    main_value = main_data[item]
                    compared_value = compared_data[item]
                    main_current = main_value * progress
                    compared_current = compared_value * progress
                    main_data_text = fmt_value(item, main_current)
                    compared_data_text = fmt_value(item, compared_current)
                    # 主数值（左侧），添加黑色1px描边
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        draw.text((left_bar_x2 - data_font.getmask(main_data_text).size[0] - 5 + dx,
                                   bar_y + (bar_height - 20) // 2 + dy),
                                  text=main_data_text, font=data_font, fill=(0, 0, 0, 255))
                    draw.text((left_bar_x2 - data_font.getmask(main_data_text).size[0] - 5,
                               bar_y + (bar_height - 20) // 2),
                              text=main_data_text, font=data_font, fill=background_color)
                    # 对比数值（右侧），添加黑色1px描边
                    for dx, dy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        draw.text((right_bar_x1 + 5 + dx,
                                   bar_y + (bar_height - 20) // 2 + dy),
                                  text=compared_data_text, font=data_font, fill=(0, 0, 0, 255))
                    draw.text((right_bar_x1 + 5,
                               bar_y + (bar_height - 20) // 2),
                              text=compared_data_text, font=data_font, fill=background_color)
            return np.array(img)

        return VideoClip(make_frame, duration=total_duration)

    # 主函数
    def create_video_with_effects(self, title, main_avatar_path, compared_avatar_path, main_body_path, compared_body_path, cover_img_path,
                                  output_path, data,
                                  audio_path, subtitlers, bg_music_path):
        # 竖版视频尺寸
        video_size = (self.width, self.height)
        audio_clip = AudioFileClip(audio_path).with_start(0.5)
        # 设置持续时间
        total_duration = audio_clip.duration + 1  # 总时长延长到30秒，因为数据对比需要时间
        animation_duration = 2  # 动画效果时长2秒
        info_start_time = 2  # 球员信息在第2.5秒开始显示
        data_start_time = 5.0  # 数据对比在第5秒开始显示

        title_mask = title_font.getmask(title)
        title_width = title_mask.size[0]
        title_height = title_mask.size[1]
        title_x = 450 - title_width / 2
        title_y = 470

        # 六边形宽度和高度
        hex_width = title_width + 100
        hex_height = title_height + 40

        # 计算六边型6个点的坐标
        hex_points = [
            (450 - hex_width / 2, title_y + hex_height / 2),  # 左上
            (450 - title_width / 2, title_y),  # 上左
            (450 + title_width / 2, title_y),  # 上右
            (450 + hex_width / 2, title_y + hex_height / 2),  # 右上
            (450 + title_width / 2, title_y + hex_height),  # 右下
            (450 - title_width / 2, title_y + hex_height)  # 左下
        ]

        # 创建静态梯形背景（从0.2秒开始出现，避免覆盖首帧封面）
        static_bg_clip = self.create_static_background(hex_points, total_duration - 0.2, title_y, hex_height).with_start(0.2)

        # 创建打字机效果（和图片动画同时开始）
        typewriter_clip = self.create_typewriter_effect(
            text=title,
            position=(title_x, title_y + 20),
            duration=animation_duration,
            total_duration=total_duration,
            bg_points=None
        )

        # 创建球员信息显示效果
        player_info_clip = self.create_player_info_effect(
            data=data,
            start_time=info_start_time + 1,
            total_duration=total_duration
        )
        # 创建球员姓名打字机效果
        name_typewriter_clip = self.create_name_typewriter_effect(
            data=data,
            start_time=info_start_time,
            total_duration=total_duration
        )

        # 创建数据对比效果（拆分为进度条与文字两层）
        data_bar_clip = self.create_data_bar_effect(
            data=data,
            start_time=data_start_time,
            total_duration=total_duration
        )
        data_text_clip = self.create_data_text_effect(
            data=data,
            start_time=data_start_time,
            total_duration=total_duration
        )

        main_body_pil_image = PilImage.open(main_body_path)
        main_body_width, main_body_height = main_body_pil_image.size

        compared_body_pil_image = PilImage.open(compared_body_path)
        compared_body_width, compared_body_height = compared_body_pil_image.size

        # 定义图片最终位置和尺寸
        positions_and_sizes = {
            'main_avatar': {'position': (30, 50)},
            'compared_avatar': {'position': (480, 50)},
            'main_body': {'position': (int((450 - main_body_width) / 2), 590 + int((700 - main_body_height) / 2))},
            'compared_body': {'position': (450 + int((450 - compared_body_width) / 2), 590 + int((700 - compared_body_height) / 2))}
        }

        main_avatar_anim = self.create_deal_animation(
            main_avatar_path,
            positions_and_sizes["main_avatar"]["position"],
            start_time=0.5,
            duration=0.2,
            total_duration=total_duration
        )

        compared_avatar_anim = self.create_deal_animation(
            compared_avatar_path,
            positions_and_sizes["compared_avatar"]["position"],
            start_time=1,  # 稍微延迟，模拟发牌效果
            duration=0.2,
            total_duration=total_duration
        )

        main_body_anim = self.create_deal_animation(
            main_body_path,
            positions_and_sizes["main_body"]["position"],
            start_time=0.5,
            duration=0.3,
            total_duration=total_duration
        )

        compared_body_anim = self.create_deal_animation(
            compared_body_path,
            positions_and_sizes["compared_body"]["position"],
            start_time=1,
            duration=0.3,
            total_duration=total_duration
        )

        # 创建黑色背景
        background = ColorClip(size=video_size, color=(0, 0, 0), duration=total_duration)

        cover_img = PilImage.open(cover_img_path).convert("RGBA")

        cover_img = cover_img.resize((self.width, self.height))
        cover_clip = ImageClip(np.array(cover_img)).with_duration(0.1)

        def make_watermark_frame(t):
            img = PilImage.new("RGBA", (850, 80), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            # paste logo
            logo_img = PilImage.open(os.path.join(LOGO_PATH, 'logo.png')).resize((80, 80)).convert("RGBA")
            img.paste(logo_img, (465, 0), mask=logo_img)
            # paste text
            draw.text((535, 20), text='数据之言', font=title_font, fill='white')

            x0, y0, x1, y1 = 460, 0, 709, 79
            # 边框动画
            cycle = 10
            t_mod = t % cycle
            if t_mod < 2:  # 前2秒绘制边框
                progress = t_mod / 2
                draw = ImageDraw.Draw(img)

                # 上边
                draw.line([(x0, y0), (x0 + (x1 - x0) * progress, y0)], fill="white", width=3)
                # 右边
                draw.line([(x1, y0), (x1, y0 + (y1 - y0) * progress)], fill="white", width=3)
                # 下边
                draw.line([(x1, y1), (x1 - (x1 - x0) * progress, y1)], fill="white", width=3)
                # 左边
                draw.line([(x0, y1), (x0, y1 - (y1 - y0) * progress)], fill="white", width=3)
            elif t_mod < 5:
                draw.rectangle([x0, y0, x1, y1], outline="white", width=3)

            return np.array(img)

        watermark_clip = VideoClip(make_watermark_frame, duration=total_duration).with_position((50, video_size[1] - 200))

        final_video = CompositeVideoClip([
            background,
            cover_clip,
            main_avatar_anim,
            compared_avatar_anim,
            static_bg_clip.with_position((0, 0)),  # 静态梯形背景
            typewriter_clip.with_position((0, 0)),  # 标题打字机文字
            name_typewriter_clip.with_position((0, 0)),  # 球员姓名打字机
            player_info_clip.with_position((0, 0)),  # 球员信息（在图片之前）
            data_bar_clip.with_position((0, 0)),  # 进度条在 body 照片前一层（下层）
            main_body_anim,  # 主体全身照
            compared_body_anim,  # 对比主体全身照
            data_text_clip.with_position((0, 0)),  # 数值文字在 body 照片后一层（上层）
            watermark_clip,
            *subtitlers
        ], size=video_size).with_duration(total_duration)
        # 背景音乐：全程，匹配总时长
        bg_music = AudioFileClip(bg_music_path).with_volume_scaled(0.1).with_duration(total_duration)
        bg_music = bg_music.with_effects([AudioFadeOut(1)])
        # 合并音轨
        final_audio = CompositeAudioClip([audio_clip, bg_music])
        final_video = final_video.with_audio(final_audio)

        # 输出
        try:
            final_video.write_videofile(
                output_path,
                fps=30,
                codec="libx264",
                audio_codec="aac",
                audio_bitrate="192k",
                ffmpeg_params=["-crf", "18", "-preset", "slow", "-pix_fmt", "yuv420p"]
            )
        finally:
            try:
                if hasattr(audio_clip, "close"):
                    audio_clip.close()
            except Exception:
                pass
            try:
                if hasattr(bg_music, "close"):
                    bg_music.close()
            except Exception:
                pass
            try:
                if hasattr(final_audio, "close"):
                    final_audio.close()
            except Exception:
                pass
            try:
                final_video.close()
            except Exception:
                pass

    # 图片预处理函数
    @staticmethod
    def limit_body_height(img, max_w, max_h):
        w, h = img.size
        scale = min(max_w / w, max_h / h)
        new_w = int(w * scale)
        new_h = int(h * scale)
        return img.resize((new_w, new_h), PilImage.LANCZOS)

    def generate_vertical_cover(self, title, main_name, compared_name, main_img, compared_img, user):
        width, height = 1080, 1464

        bg = PilImage.open(os.path.join(self.img_path, "1b6db0a6-91fb-4401-b60e-9ec1c51976dd.png")).resize((width, height))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.2)

        draw = ImageDraw.Draw(bg)
        font_path = "msyhbd.ttc"
        if not os.path.exists(font_path):
             font_path = "STXINWEI.TTF"

        title_font = ImageFont.truetype(font_path, 90)
        title_color = (255, 215, 0)
        stroke_color = (0, 0, 0)

        def draw_text_with_stroke(draw_obj, pos, text, font, fill, stroke_fill, stroke_width=2, align="center"):
            x, y = pos
            for dx in range(-stroke_width, stroke_width):
                for dy in range(-stroke_width, stroke_width):
                    if dx != 0 or dy != 0:
                        draw_obj.text((x + dx, y + dy), text, font=font, fill=stroke_fill, align=align)
            draw_obj.text((x, y), text, font=font, fill=fill, align=align)

        # 绘制标题
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_w = title_bbox[2] - title_bbox[0]
        title_x = (width - title_w) // 2
        title_y = 200
        draw_text_with_stroke(draw, (title_x, title_y), title, title_font, title_color, stroke_color, 3)

        target_width = width // 2
        max_height = height // 2

        main_body = PilImage.open(main_img).convert("RGBA")
        main_body = self.limit_body_height(main_body, target_width, max_height)

        compared_body = PilImage.open(compared_img).convert("RGBA")
        compared_body = self.limit_body_height(compared_body, target_width, max_height)

        # === 人物水平居中分列 + 垂直居中对齐 ===
        bg_center_y = height // 2
        main_y = bg_center_y - main_body.height // 2
        compared_y = bg_center_y - compared_body.height // 2

        bg.paste(main_body, (0, main_y), main_body)
        bg.paste(compared_body, (target_width, compared_y), compared_body)

        # === 文字和字体 ===

        compare_title_font = ImageFont.truetype("msyhbd.ttc", 80)
        vs_font = ImageFont.truetype("ARLRDBD.TTF", 80)

        compare_title_color = (255, 215, 0)  # 金色
        stroke_color = (0, 0, 0)
        vs_color = (255, 255, 255)  # 白色

        # === 计算文字大小 ===
        dummy_draw = ImageDraw.Draw(bg)

        def split_name(name):
            if '·' in name:
                return name.split('·')
            else:
                return [name]

        main_lines = split_name(main_name)
        compared_lines = split_name(compared_name)

        # === 计算姓名文本高度（考虑左右不同行数，保持居中） ===
        line_height = compare_title_font.getbbox("测试")[3] - compare_title_font.getbbox("测试")[1]
        line_spacing = 20
        main_total_height = len(main_lines) * line_height + max(len(main_lines) - 1, 0) * line_spacing
        compared_total_height = len(compared_lines) * line_height + max(len(compared_lines) - 1, 0) * line_spacing
        total_name_height = max(main_total_height, compared_total_height)

        # === VS文字（改为竖线） ===
        vs_text = "|"
        vs_bbox = dummy_draw.textbbox((0, 0), vs_text, font=vs_font)
        vs_w = vs_bbox[2] - vs_bbox[0]
        vs_h = vs_bbox[3] - vs_bbox[1]

        # === 计算左右两边姓名位置 ===
        left_block_center_x = width // 2 - vs_w // 2 - 20
        right_block_center_x = width // 2 + vs_w // 2 + 20
        text_base_y = height // 2 - 150  # 稍微靠下放（原贴纸区）

        draw = ImageDraw.Draw(bg)

        # 左右姓名垂直居中对齐
        main_start_y = text_base_y + (total_name_height - main_total_height) // 2
        compared_start_y = text_base_y + (total_name_height - compared_total_height) // 2

        for i, line in enumerate(main_lines):
            lw, _ = draw.textbbox((0, 0), line, font=compare_title_font)[2:]
            x = left_block_center_x - lw
            y = main_start_y + i * (line_height + line_spacing)
            draw_text_with_stroke(draw, (x, y), line, compare_title_font, compare_title_color, stroke_color, 3)

        for i, line in enumerate(compared_lines):
            x = right_block_center_x
            y = compared_start_y + i * (line_height + line_spacing)
            draw_text_with_stroke(draw, (x, y), line, compare_title_font, compare_title_color, stroke_color, 3)

        # 绘制分隔竖线
        vs_x = (width - vs_w) // 2
        vs_y = text_base_y + (total_name_height - vs_h) // 2 - 10
        draw_text_with_stroke(draw, (vs_x, vs_y), vs_text, vs_font, vs_color, stroke_color, 3)

        image_id = uuid.uuid4()
        image_name = f'{image_id}.png'
        bg.save(os.path.join(IMG_PATH, image_name))
        cover_size = os.path.getsize(os.path.join(IMG_PATH, image_name))
        spec = {
            'format': 'png',
            'mode': 'RGBA',
            'size': cover_size
        }

        Image(
            id=image_id,
            img_name=image_name,
            category='normal',
            img_path=IMG_PATH,
            width=1200,
            height=1600,
            creator=user,
            spec=spec
        ).save()

        return image_id

    def generate_horizontal_cover(self, main_name, compared_name, main_img, compared_img, user):
        width, height = 1920, 1080

        bg = PilImage.open(os.path.join(self.img_path, "6b24e082-f935-4664-8bd4-4c9e228d44e8.png")).resize((width, height))
        enhancer = ImageEnhance.Brightness(bg)
        bg = enhancer.enhance(0.2)

        target_height = height - 100

        main_body = PilImage.open(main_img).convert("RGBA")
        w, h = main_body.size
        new_w = int(w * target_height / h)
        main_body = main_body.resize((new_w, target_height), PilImage.LANCZOS)
        main_x = width // 4 - new_w // 2

        compared_body = PilImage.open(compared_img).convert("RGBA")
        w, h = compared_body.size
        new_w = int(w * target_height / h)
        compared_body = compared_body.resize((new_w, target_height), PilImage.LANCZOS)
        compared_x = width * 3 // 4 - new_w // 2

        bg.paste(main_body, (main_x, 50), main_body)
        bg.paste(compared_body, (compared_x, 50), compared_body)

        # === 绘制文字函数（带描边） ===
        def draw_text_with_stroke(draw_obj, pos, text, font, fill, stroke_fill, stroke_width=2, align="center"):
            x, y = pos
            for dx in range(-stroke_width, stroke_width):
                for dy in range(-stroke_width, stroke_width):
                    if dx != 0 or dy != 0:
                        draw_obj.text((x + dx, y + dy), text, font=font, fill=stroke_fill, align=align)
            draw_obj.text((x, y), text, font=font, fill=fill, align=align)

        # === 文字和字体 ===

        compare_title_font = ImageFont.truetype("msyhbd.ttc", 120)
        vs_font = ImageFont.truetype("ARLRDBD.TTF", 120)

        compare_title_color = (255, 215, 0)  # 金色
        stroke_color = (0, 0, 0)
        vs_color = (255, 255, 255)  # 白色

        # === 计算文字大小 ===
        dummy_draw = ImageDraw.Draw(bg)

        def split_name(name):
            if '·' in name:
                return name.split('·')
            else:
                return [name]

        main_lines = split_name(main_name)
        compared_lines = split_name(compared_name)

        # === 计算姓名文本高度（考虑左右不同行数，保持居中） ===
        line_height = compare_title_font.getbbox("测试")[3] - compare_title_font.getbbox("测试")[1]
        line_spacing = 20
        main_total_height = len(main_lines) * line_height + max(len(main_lines) - 1, 0) * line_spacing
        compared_total_height = len(compared_lines) * line_height + max(len(compared_lines) - 1, 0) * line_spacing
        total_name_height = max(main_total_height, compared_total_height)

        # === VS文字（改为竖线） ===
        vs_text = "|"
        vs_bbox = dummy_draw.textbbox((0, 0), vs_text, font=vs_font)
        vs_w = vs_bbox[2] - vs_bbox[0]
        vs_h = vs_bbox[3] - vs_bbox[1]

        # === 计算左右两边姓名位置 ===
        left_block_center_x = width // 2 - vs_w // 2 - 20
        right_block_center_x = width // 2 + vs_w // 2 + 20
        text_base_y = int(height * (1 - 0.618))

        draw = ImageDraw.Draw(bg)

        # 左右姓名垂直居中对齐
        main_start_y = text_base_y + (total_name_height - main_total_height) // 2
        compared_start_y = text_base_y + (total_name_height - compared_total_height) // 2

        for i, line in enumerate(main_lines):
            lw, _ = draw.textbbox((0, 0), line, font=compare_title_font)[2:]
            x = left_block_center_x - lw
            y = main_start_y + i * (line_height + line_spacing)
            draw_text_with_stroke(draw, (x, y), line, compare_title_font, compare_title_color, stroke_color, 3)

        for i, line in enumerate(compared_lines):
            x = right_block_center_x
            y = compared_start_y + i * (line_height + line_spacing)
            draw_text_with_stroke(draw, (x, y), line, compare_title_font, compare_title_color, stroke_color, 3)

        # 绘制分隔竖线
        vs_x = (width - vs_w) // 2
        vs_y = text_base_y + (total_name_height - vs_h) // 2 - 10
        draw_text_with_stroke(draw, (vs_x, vs_y), vs_text, vs_font, vs_color, stroke_color, 3)

        image_id = uuid.uuid4()
        image_name = f'{image_id}.png'
        bg.save(os.path.join(IMG_PATH, image_name))
        cover_size = os.path.getsize(os.path.join(IMG_PATH, image_name))
        spec = {
            'format': 'png',
            'mode': 'RGBA',
            'size': cover_size
        }

        Image(
            id=image_id,
            img_name=image_name,
            category='normal',
            img_path=IMG_PATH,
            width=width,
            height=height,
            creator=user,
            spec=spec
        ).save()

        return image_id
