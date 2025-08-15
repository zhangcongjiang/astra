# 新闻采集分析插件

## 功能概述

新闻采集分析插件是一个基于Django的视频模板插件，用于根据用户输入的话题自动采集相关新闻，并使用多个AI模型进行客观评价分析，最终生成评价卡片图片存储到素材库。

## 主要功能

1. **新闻搜索**: 调用Google News API根据话题搜索相关新闻
2. **关键词分析**: 使用智普AI分析新闻简介，提取3个关键词
3. **扩展搜索**: 根据关键词进行二次新闻搜索
4. **内容提取**: 使用trafilatura提取新闻文章的完整内容和标题
5. **AI评价**: 支持多个AI模型（OpenAI、Claude、DeepSeek、豆包、Kimi、Gemini）对新闻进行客观评价
6. **卡片生成**: 将AI评价结果生成美观的卡片图片并保存到素材库

## 插件参数

- **新闻话题** (必填): 用户想要分析的新闻话题，如"武汉大学图书馆"
- **文章内容最大长度** (可选): 提取文章内容的最大字符数，默认5000字符
- **AI评价模型** (必填): 选择用于评价新闻的AI模型，支持多选

## 支持的AI模型

- OpenAI GPT
- Claude
- DeepSeek
- 豆包 (Doubao)
- Kimi
- Gemini

## 技术实现

### 依赖包

- `requests`: HTTP请求库
- `trafilatura`: 网页内容提取
- `PIL (Pillow)`: 图像处理
- `textwrap`: 文本换行处理

### API配置

插件需要配置以下API密钥：

- Google News API: `https://google-news-worker.linfree.workers.dev/`
- 智普AI API: `https://open.bigmodel.cn/api/paas/v4/`
- 各AI模型的API密钥

### 工作流程

1. 接收用户输入的话题参数
2. 调用Google News API搜索初始新闻列表
3. 使用智普AI分析新闻简介，提取3个关键词
4. 根据关键词再次搜索新闻，扩大搜索范围
5. 对所有新闻URL进行去重处理
6. 使用trafilatura提取每篇文章的完整内容和标题
7. 将文章内容发送给选定的AI模型进行客观评价
8. 生成包含AI评价的卡片图片
9. 将卡片图片保存到Django的素材库中

## 使用方法

### 1. 安装依赖

```bash
pip install trafilatura==1.12.2
```

### 2. 配置API密钥

在插件代码中配置各AI模型的API密钥：

```python
self.zhipu_api_key = "your_zhipu_api_key"
self.openai_api_key = "your_openai_api_key"
self.claude_api_key = "your_claude_api_key"
# ... 其他API密钥
```

### 3. 调用插件

通过Django的视频模板系统调用插件：

```python
from video.templates.news_analysis_plugin import NewsAnalysisPlugin

plugin = NewsAnalysisPlugin()
result = plugin.process(user_id, video_id, {
    'topic': '人工智能',
    'max_content_length': 5000,
    'ai_models': ['openai', 'claude']
})
```

## 输出结果

插件会生成以下内容：

1. **新闻数据**: 采集到的新闻文章内容和元数据
2. **AI评价**: 各AI模型对新闻事件的客观评价
3. **卡片图片**: 包含AI评价内容的美观卡片图片，保存在素材库中

## 注意事项

1. 确保所有API密钥都已正确配置
2. 网络连接稳定，因为需要调用多个外部API
3. 根据使用量合理设置文章内容长度限制
4. 定期检查API配额使用情况
5. 生成的卡片图片会占用存储空间，注意定期清理

## 错误处理

插件包含完善的错误处理机制：

- API调用失败时会记录错误日志
- 网络超时会自动重试
- 无效的新闻URL会被跳过
- AI模型调用失败时会继续处理其他模型

## 扩展性

插件设计具有良好的扩展性：

- 可以轻松添加新的AI模型支持
- 可以自定义卡片图片的样式和布局
- 可以调整新闻搜索和内容提取的参数
- 可以集成其他新闻源API