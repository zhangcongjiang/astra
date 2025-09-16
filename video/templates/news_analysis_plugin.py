import logging
import os
import traceback
import uuid
import json
import requests
import base64
import time
from urllib.parse import quote
from PIL import Image as PilImage, ImageDraw, ImageFont
import trafilatura
from io import BytesIO

from image.models import Image
from astra.settings import IMG_PATH
from video.templates.video_template import VideoTemplate, VideoOrientation

logger = logging.getLogger("video")


class NewsAnalysisPlugin(VideoTemplate):
    """
    新闻采集和分析插件
    功能：
    1. 根据用户输入话题搜索新闻
    2. 使用智普AI分析关键词
    3. 进一步搜索相关新闻
    4. 提取文章内容
    5. 调用多个AI进行客观评价
    6. 生成卡片图片存储到素材库
    """

    def __init__(self):
        super().__init__()
        self.template_id = str(uuid.uuid3(uuid.NAMESPACE_DNS, self.__class__.__name__))
        self.name = '新闻采集分析插件'
        self.desc = '根据话题采集新闻，AI分析生成评价卡片'
        self.description = '根据用户输入的话题，采集相关新闻并使用多个AI模型进行客观评价分析'
        self.parameters = '''
        {"form":[
            {
                "name":"topic",
                "label":"新闻话题",
                "type":"input",
                "inputType":"text",
                "required":true,
                "placeholder":"请输入要分析的新闻话题",
                "description":"输入您想要分析的新闻话题，如：武汉大学图书馆"
            },
            {
                "name":"max_content_length",
                "label":"文章内容最大长度",
                "type":"input",
                "inputType":"number",
                "required":false,
                "placeholder":"5000",
                "description":"提取文章内容的最大字符数，默认5000字符"
            },
            {
                "name":"ai_models",
                "label":"AI评价模型",
                "type":"select",
                "multiple":true,
                "required":true,
                "options":{
                    "source":"static",
                    "data":[
                        {"value":"openai","label":"OpenAI GPT"},
                        {"value":"claude","label":"Claude"},
                        {"value":"deepseek","label":"DeepSeek"},
                        {"value":"doubao","label":"豆包"},
                        {"value":"kimi","label":"Kimi"},
                        {"value":"gemini","label":"Gemini"}
                    ]
                },
                "description":"选择用于评价新闻的AI模型"
            }
        ]}
        '''
        self.parameters = json.loads(self.parameters)
        self.orientation = VideoOrientation.HORIZONTAL.name
        self.demo = None
        self.cover = None
        self.video_type = 'JianYing'
        
        # API配置
        self.google_news_api = "https://google-news-worker.linfree.workers.dev/"
        self.zhipu_api_base = "https://open.bigmodel.cn/api/paas/v4/"
        self.zhipu_api_key = os.getenv("ZHIPU_API_KEY")  # 需要配置

        
        # AI模型配置
        self.ai_configs = {
            "openai": {
                "api_key": "",
                "base_url": "https://api.openai.com/v1/",
                "model": "gpt-3.5-turbo"
            },
            "claude": {
                "api_key": "",
                "base_url": "https://api.anthropic.com/",
                "model": "claude-3-sonnet-20240229"
            },
            "deepseek": {
                "api_key": os.getenv("DEEPSEEK_API_KEY"),

                "base_url": "https://api.deepseek.com/",
                "model": "deepseek-chat"
            },
            "doubao": {
                "api_key": "",
                "base_url": "https://ark.cn-beijing.volces.com/api/v3/",
                "model": "doubao-pro-4k"
            },
            "kimi": {
                "api_key": os.getenv("KIMI_API_KEY"),
                "base_url": "https://api.moonshot.cn/v1/",
                "model": "moonshot-v1-8k"
            },
            "gemini": {
                "api_key": "",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/",
                "model": "gemini-pro"
            }
        }

    def process(self, user, video_id, parameters):
        """
        处理新闻采集和分析流程
        
        Args:
            user: 用户ID
            video_id: 视频ID（这里用作任务ID）
            parameters: 参数字典
        """
        logger.info(f"新闻分析插件开始处理，参数：{parameters}")
        
        try:
            topic = parameters.get('topic')
            max_content_length = int(parameters.get('max_content_length', 5000))
            ai_models = parameters.get('ai_models', [])
            
            if not topic:
                raise ValueError("话题不能为空")
            
            if not ai_models:
                raise ValueError("请至少选择一个AI模型")
            
            # 步骤1: 搜索初始新闻
            logger.info(f"步骤1: 搜索话题 '{topic}' 的新闻")
            initial_news = self.search_news(topic)
            
            if not initial_news or not initial_news.get('news'):
                logger.warning(f"无法从API获取关于 '{topic}' 的新闻，可能是网络问题或API限制")
                # 提供一个基础的错误处理，而不是直接抛出异常
                return {
                    'task_id': video_id,
                    'topic': topic,
                    'error': 'news_search_failed',
                    'message': f"暂时无法获取关于 '{topic}' 的新闻数据，请稍后重试。可能原因：API请求限制、网络连接问题或代理设置问题。",
                    'total_news': 0,
                    'total_articles': 0,
                    'evaluations_count': 0,
                    'card_images': []
                }
            
            # 步骤2: 使用智普AI分析关键词
            logger.info("步骤2: 使用智普AI分析关键词")
            introductions = [news['introduction'] for news in initial_news['news']]
            keywords = self.analyze_keywords_with_zhipu(introductions)
            
            # 步骤3: 根据关键词搜索更多新闻
            logger.info(f"步骤3: 根据关键词 {keywords} 搜索更多新闻")
            all_news = []
            all_news.extend(initial_news['news'])
            
            # 记录成功和失败的关键词搜索
            successful_keywords = 0
            failed_keywords = 0
            
            for keyword in keywords:
                try:
                    keyword_news = self.search_news(keyword)
                    if keyword_news and keyword_news.get('news'):
                        all_news.extend(keyword_news['news'])
                        successful_keywords += 1
                        logger.info(f"关键词 '{keyword}' 搜索成功，获得 {len(keyword_news['news'])} 条新闻")
                    else:
                        failed_keywords += 1
                        logger.warning(f"关键词 '{keyword}' 搜索失败或无结果")
                except Exception as e:
                    failed_keywords += 1
                    logger.warning(f"关键词 '{keyword}' 搜索出错: {str(e)}")
            
            logger.info(f"关键词搜索完成: 成功 {successful_keywords} 个，失败 {failed_keywords} 个")
            
            # 步骤4: 去重
            unique_news = self.deduplicate_news(all_news)
            logger.info(f"去重后共有 {len(unique_news)} 条新闻")
            
            # 步骤5: 提取文章内容
            logger.info("步骤5: 提取文章内容")
            articles = self.extract_articles_content(unique_news, max_content_length)
            
            # 步骤6: AI评价
            logger.info("步骤6: 调用AI进行评价")
            evaluations = self.get_ai_evaluations(articles, ai_models, topic)
            
            # 步骤7: 生成卡片图片
            logger.info("步骤7: 生成评价卡片图片")
            card_images = self.generate_evaluation_cards(evaluations, user, topic)
            
            logger.info(f"新闻分析插件处理完成，生成了 {len(card_images)} 张卡片图片")
            
            return {
                'task_id': video_id,
                'topic': topic,
                'total_news': len(unique_news),
                'total_articles': len(articles),
                'evaluations_count': len(evaluations),
                'card_images': card_images
            }
            
        except Exception as e:
            logger.error(f"新闻分析插件处理失败: {traceback.format_exc()}")
            raise e

    def search_news(self, query):
        """
        搜索新闻（带重试机制）
        
        Args:
            query: 搜索关键词
            
        Returns:
            dict: 新闻搜索结果
        """
        encoded_query = quote(query)
        url = f"{self.google_news_api}?query={encoded_query}"
        
        # 配置代理
        proxies = {
            'http': 'http://127.0.0.1:1080',
            'https': 'http://127.0.0.1:1080'
        }
        
        # 重试配置
        max_retries = 3
        retry_delays = [2, 5, 10]  # 递增延迟时间（秒）
        
        for attempt in range(max_retries):
            try:
                logger.info(f"尝试搜索新闻，第 {attempt + 1} 次尝试")
                response = requests.get(url, proxies=proxies, timeout=30)
                
                if response.status_code == 200:
                    return response.json()
                elif response.status_code == 429:
                    # 请求过于频繁，等待后重试
                    if attempt < max_retries - 1:
                        delay = retry_delays[attempt]
                        logger.warning(f"请求过于频繁 (429)，等待 {delay} 秒后重试")
                        time.sleep(delay)
                        continue
                    else:
                        logger.error(f"搜索新闻失败，已达到最大重试次数: 429 Too Many Requests")
                        break
                else:
                    response.raise_for_status()
                    
            except requests.exceptions.Timeout:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"请求超时，等待 {delay} 秒后重试")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"搜索新闻失败，请求超时且已达到最大重试次数")
                    break
            except Exception as e:
                if attempt < max_retries - 1:
                    delay = retry_delays[attempt]
                    logger.warning(f"搜索新闻出错: {str(e)}，等待 {delay} 秒后重试")
                    time.sleep(delay)
                    continue
                else:
                    logger.error(f"搜索新闻失败: {str(e)}")
                    break
        
        return None

    def analyze_keywords_with_zhipu(self, introductions):
        """
        使用智普AI分析关键词
        
        Args:
            introductions: 新闻简介列表
            
        Returns:
            list: 关键词列表
        """
        try:
            # 构建提示词
            intro_text = "\n".join(introductions[:10])  # 最多取前10条
            logger.info(f"intro_text={intro_text}")
            prompt = f"""
            作为一名明锐的新闻记者，请分析以下新闻简介，找出需要进一步调查的3个关键字。
            这些关键字应该能帮助我们更深入地了解这个事件的各个方面。
            
            新闻简介：
            {intro_text}
            
            请直接返回3个关键字，用逗号分隔，不要其他解释。
            """
            
            headers = {
                "Authorization": f"Bearer {self.zhipu_api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": "glm-4-flash",
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "temperature": 0.7
            }
            
            response = requests.post(
                f"{self.zhipu_api_base}chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            response.raise_for_status()
            
            result = response.json()
            keywords_text = result['choices'][0]['message']['content'].strip()
            keywords = [kw.strip() for kw in keywords_text.split(',')]
            
            logger.info(f"智普AI分析得到关键词: {keywords}")
            return keywords[:3]  # 确保只返回3个关键词
            
        except Exception as e:
            logger.error(f"智普AI分析关键词失败: {str(e)}")
            # 返回默认关键词
            return ["相关事件", "最新进展", "官方回应"]

    def deduplicate_news(self, news_list):
        """
        新闻去重
        
        Args:
            news_list: 新闻列表
            
        Returns:
            list: 去重后的新闻列表
        """
        seen_urls = set()
        unique_news = []
        
        for news in news_list:
            # 支持多种URL字段名
            url = news.get('address', '') or news.get('url', '') or news.get('link', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                unique_news.append(news)
        
        return unique_news

    def extract_articles_content(self, news_list, max_length):
        """
        提取文章内容
        
        Args:
            news_list: 新闻列表
            max_length: 最大内容长度
            
        Returns:
            list: 文章内容列表
        """
        articles = []
        
        for news in news_list:
            try:
                url = news.get('address')
                if not url:
                    continue
                
                # 使用requests下载内容，设置30秒超时
                try:
                    response = requests.get(url, timeout=30, headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
                    })
                    response.raise_for_status()
                    downloaded = response.text
                except requests.exceptions.RequestException as req_e:
                    logger.warning(f"下载文章失败 {url}: {str(req_e)}")
                    continue
                
                if downloaded:
                    content = trafilatura.extract(downloaded)
                    if content:
                        # 截断内容
                        if len(content) > max_length:
                            content = content[:max_length] + "..."
                        
                        articles.append({
                            'title': news.get('title', ''),
                            'url': url,
                            'source': news.get('source', ''),
                            'content': content
                        })
                        
                        logger.info(f"成功提取文章: {news.get('title', '')[:50]}...")
                    
            except Exception as e:
                logger.warning(f"提取文章内容失败 {url}: {str(e)}")
                continue
        
        return articles

    def get_ai_evaluations(self, articles, ai_models, topic):
        """
        获取AI评价
        
        Args:
            articles: 文章列表
            ai_models: AI模型列表
            topic: 话题
            
        Returns:
            list: AI评价列表
        """
        evaluations = []
        
        # 构建文章摘要
        articles_summary = "\n\n".join([
            f"标题: {article['title']}\n来源: {article['source']}\n内容: {article['content'][:500]}..."
            for article in articles[:5]  # 最多取前5篇文章
        ])
        
        prompt = f"""
        请作为一名客观的新闻分析师，对以下关于"{topic}"的新闻事件进行客观评价。
        
        新闻内容：
        {articles_summary}
        
        请从以下几个角度进行分析：
        1. 事件的客观事实
        2. 各方观点和立场
        3. 可能的影响和后果
        4. 需要关注的问题
        
        请保持客观中立，避免主观判断，字数控制在300字以内。
        """
        
        for model_name in ai_models:
            try:
                evaluation = self.call_ai_model(model_name, prompt)
                if evaluation:
                    evaluations.append({
                        'model': model_name,
                        'evaluation': evaluation,
                        'topic': topic
                    })
                    logger.info(f"{model_name} 评价完成")
                    
            except Exception as e:
                logger.error(f"{model_name} 评价失败: {str(e)}")
                continue
        
        return evaluations

    def call_ai_model(self, model_name, prompt):
        """
        调用AI模型
        
        Args:
            model_name: 模型名称
            prompt: 提示词
            
        Returns:
            str: AI回复
        """
        config = self.ai_configs.get(model_name)
        if not config:
            raise ValueError(f"不支持的AI模型: {model_name}")
        
        # 这里需要根据不同的AI模型实现不同的调用逻辑
        # 由于每个AI的API格式不同，这里提供一个通用的OpenAI格式示例
        
        headers = {
            "Authorization": f"Bearer {config['api_key']}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": config['model'],
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": 0.7,
            "max_tokens": 500
        }
        
        response = requests.post(
            f"{config['base_url']}chat/completions",
            headers=headers,
            json=data,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        return result['choices'][0]['message']['content'].strip()

    def generate_evaluation_cards(self, evaluations, user, topic):
        """
        生成评价卡片图片
        
        Args:
            evaluations: 评价列表
            user: 用户ID
            topic: 话题
            
        Returns:
            list: 生成的图片信息列表
        """
        card_images = []
        
        for evaluation in evaluations:
            try:
                # 创建卡片图片
                img = self.create_evaluation_card(
                    evaluation['model'],
                    evaluation['evaluation'],
                    topic
                )
                
                # 保存图片
                image_id = str(uuid.uuid4())
                image_filename = f"{image_id}.png"
                image_path = os.path.join(IMG_PATH, image_filename)
                
                img.save(image_path, 'PNG')
                
                # 保存到数据库
                image_record = Image.objects.create(
                    id=image_id,
                    img_name=image_filename,
                    img_path=image_path,
                    width=img.width,
                    height=img.height,
                    origin="AI生成",
                    category="normal",
                    creator=str(user),
                    spec={
                        'type': 'news_evaluation_card',
                        'topic': topic,
                        'ai_model': evaluation['model'],
                        'generated_by': 'news_analysis_plugin'
                    }
                )
                
                card_images.append({
                    'image_id': str(image_record.id),
                    'filename': image_filename,
                    'ai_model': evaluation['model'],
                    'topic': topic
                })
                
                logger.info(f"生成卡片图片: {evaluation['model']} - {image_filename}")
                
            except Exception as e:
                logger.error(f"生成卡片图片失败 {evaluation['model']}: {str(e)}")
                continue
        
        return card_images

    def create_evaluation_card(self, model_name, evaluation_text, topic):
        """
        通过MD2Card API创建评价卡片图片
        
        Args:
            model_name: AI模型名称
            evaluation_text: 评价文本
            topic: 话题
            
        Returns:
            PIL.Image: 卡片图片
        """
        try:
            # 构建Markdown内容
            markdown_content = f"""# 新闻分析: {topic}

## AI模型: {model_name.upper()}

{evaluation_text}"""
            
            # MD2Card API配置
            url = "https://md2card.cn/api/generate"
            headers = {
                "x-api-key": "sk-7Xhczvbwo9DnRh6dekcoRwndw_YGbrmw",
                "Content-Type": "application/json"
            }
            payload = {
                "markdown": markdown_content,
                "theme": "apple-notes",
                "width": 800,
                "height": 600
            }
            
            # 调用API
            response = requests.post(url, headers=headers, data=json.dumps(payload), timeout=30)
            
            if response.status_code == 200:
                 data = response.json()
                 
                 # 检查API响应
                 if data.get('success') and 'images' in data and len(data['images']) > 0:
                     # 获取第一张图片的URL
                     image_url = data['images'][0]['url']
                     # 下载生成的图片
                     img_response = requests.get(image_url, timeout=30)
                     if img_response.status_code == 200:
                         img = PilImage.open(BytesIO(img_response.content))
                         return img
                     else:
                         logger.error(f"下载卡片图片失败: {img_response.status_code}")
                 elif 'image_url' in data:
                     # 兼容旧格式：直接返回image_url
                     img_response = requests.get(data['image_url'], timeout=30)
                     if img_response.status_code == 200:
                         img = PilImage.open(BytesIO(img_response.content))
                         return img
                     else:
                         logger.error(f"下载卡片图片失败: {img_response.status_code}")
                 elif 'image_base64' in data:
                     # 处理base64编码的图片
                     img_data = base64.b64decode(data['image_base64'])
                     img = PilImage.open(BytesIO(img_data))
                     return img
                 else:
                     logger.error(f"API响应格式异常: {data}")
            else:
                logger.error(f"MD2Card API调用失败: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"调用MD2Card API失败: {str(e)}")
        
        # 如果API调用失败，回退到原始的PIL生成方式
        return self.create_fallback_card(model_name, evaluation_text, topic)

    def create_fallback_card(self, model_name, evaluation_text, topic):
        """
        备用的PIL卡片生成方法（当API调用失败时使用）
        
        Args:
            model_name: AI模型名称
            evaluation_text: 评价文本
            topic: 话题
            
        Returns:
            PIL.Image: 卡片图片
        """
        # 卡片尺寸
        width, height = 800, 600
        
        # 创建图片
        img = PilImage.new('RGB', (width, height), color='white')
        draw = ImageDraw.Draw(img)
        
        # 尝试加载字体
        try:
            title_font = ImageFont.truetype(self.font, 32)
            model_font = ImageFont.truetype(self.font, 24)
            content_font = ImageFont.truetype(self.font, 18)
        except:
            # 如果字体加载失败，使用默认字体
            title_font = ImageFont.load_default()
            model_font = ImageFont.load_default()
            content_font = ImageFont.load_default()
        
        # 绘制标题
        title = f"新闻分析: {topic}"
        title_bbox = draw.textbbox((0, 0), title, font=title_font)
        title_width = title_bbox[2] - title_bbox[0]
        draw.text(((width - title_width) // 2, 30), title, fill='black', font=title_font)
        
        # 绘制AI模型名称
        model_text = f"AI模型: {model_name.upper()}"
        draw.text((50, 100), model_text, fill='blue', font=model_font)
        
        # 绘制评价内容
        y_offset = 150
        max_width = width - 100
        
        # 文本换行处理
        lines = self.wrap_text(evaluation_text, content_font, max_width, draw)
        
        for line in lines:
            if y_offset > height - 100:  # 防止文本超出图片边界
                break
            draw.text((50, y_offset), line, fill='black', font=content_font)
            y_offset += 25
        
        # 绘制边框
        draw.rectangle([10, 10, width-10, height-10], outline='gray', width=2)
        
        return img

    def wrap_text(self, text, font, max_width, draw):
        """
        文本换行处理
        
        Args:
            text: 文本内容
            font: 字体
            max_width: 最大宽度
            draw: 绘制对象
            
        Returns:
            list: 换行后的文本列表
        """
        lines = []
        words = text.split()
        current_line = ""
        
        for word in words:
            test_line = current_line + " " + word if current_line else word
            bbox = draw.textbbox((0, 0), test_line, font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        
        if current_line:
            lines.append(current_line)
        
        return lines