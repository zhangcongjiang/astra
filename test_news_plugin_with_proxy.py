#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试新闻分析插件的功能（包含代理配置）
"""

import os
import sys
import django
import time

# 添加项目路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'astra.settings')
django.setup()

from video.templates.news_analysis_plugin import NewsAnalysisPlugin

def test_proxy_connection():
    """
    测试代理连接
    """
    print("=== 测试代理连接 ===")
    import requests
    
    try:
        proxies = {
            'http': 'http://127.0.0.1:1080',
            'https': 'http://127.0.0.1:1080'
        }
        
        # 测试代理连接
        response = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=10)
        if response.status_code == 200:
            print(f"✅ 代理连接成功，IP信息: {response.json()}")
            return True
        else:
            print(f"❌ 代理连接失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 代理连接测试失败: {str(e)}")
        return False

def test_news_search():
    """
    测试新闻搜索功能
    """
    print("\n=== 测试新闻搜索功能 ===")
    
    plugin = NewsAnalysisPlugin()
    
    test_topics = ['武汉大学图书馆', '新能源汽车', '量子计算']
    
    for topic in test_topics:
        print(f"\n搜索话题: {topic}")
        try:
            start_time = time.time()
            news_response = plugin.search_news(topic)
            end_time = time.time()
            
            if news_response and news_response.get('news'):
                news_list = news_response['news']
                print(f"✅ 找到 {len(news_list)} 条新闻，耗时: {end_time - start_time:.2f}秒")
                
                # 显示前3条新闻标题
                for i, news in enumerate(news_list[:3]):
                    title = news.get('title', 'N/A')[:50] + '...' if len(news.get('title', '')) > 50 else news.get('title', 'N/A')
                    print(f"  {i+1}. {title}")
                    
                return news_list
            else:
                print(f"❌ 搜索 '{topic}' 失败或没有找到新闻")
                
        except Exception as e:
            print(f"❌ 搜索 '{topic}' 时出现错误: {str(e)}")
            
    return None

def test_keyword_analysis(news_list):
    """
    测试关键词分析功能
    """
    print("\n=== 测试关键词分析功能 ===")
    
    if not news_list:
        print("❌ 没有新闻数据，跳过关键词分析测试")
        return None
        
    plugin = NewsAnalysisPlugin()
    
    try:
        # 提取新闻简介
        introductions = []
        for news in news_list[:5]:  # 取前5条新闻
            intro = news.get('introduction', '') or news.get('description', '') or news.get('title', '')
            if intro:
                introductions.append(intro)
                
        if not introductions:
            print("❌ 没有找到有效的新闻简介")
            return None
            
        print(f"准备分析 {len(introductions)} 条新闻简介...")
        
        start_time = time.time()
        keywords = plugin.analyze_keywords_with_zhipu(introductions)
        end_time = time.time()
        
        if keywords:
            print(f"✅ 关键词分析成功，耗时: {end_time - start_time:.2f}秒")
            print(f"提取的关键词: {keywords}")
            return keywords
        else:
            print("❌ 关键词分析失败")
            
    except Exception as e:
        print(f"❌ 关键词分析时出现错误: {str(e)}")
        import traceback
        traceback.print_exc()
        
    return None

def test_deduplication():
    """
    测试去重功能
    """
    print("\n=== 测试去重功能 ===")
    
    plugin = NewsAnalysisPlugin()
    
    # 创建测试数据
    test_news = [
        {'url': 'https://example.com/news1', 'title': '新闻1'},
        {'url': 'https://example.com/news2', 'title': '新闻2'},
        {'url': 'https://example.com/news1', 'title': '新闻1重复'},  # 重复URL
        {'url': 'https://example.com/news3', 'title': '新闻3'},
        {'url': 'https://example.com/news2', 'title': '新闻2重复'},  # 重复URL
    ]
    
    print(f"原始新闻数量: {len(test_news)}")
    
    try:
        deduplicated = plugin.deduplicate_news(test_news)
        print(f"✅ 去重后新闻数量: {len(deduplicated)}")
        
        for i, news in enumerate(deduplicated):
            print(f"  {i+1}. {news['title']} - {news['url']}")
            
        return len(deduplicated) == 3  # 应该剩余3条不重复的新闻
        
    except Exception as e:
        print(f"❌ 去重测试失败: {str(e)}")
        return False

def test_plugin_parameters():
    """
    测试插件参数配置
    """
    print("\n=== 测试插件参数配置 ===")
    
    try:
        plugin = NewsAnalysisPlugin()
        
        print(f"插件ID: {plugin.template_id}")
        print(f"插件名称: {plugin.name}")
        print(f"插件描述: {plugin.description}")
        
        # 检查参数配置
        if hasattr(plugin, 'parameters') and plugin.parameters:
            import json
            params = json.loads(plugin.parameters) if isinstance(plugin.parameters, str) else plugin.parameters
            
            if 'form' in params:
                print(f"✅ 参数配置正常，包含 {len(params['form'])} 个参数")
                for param in params['form']:
                    print(f"  - {param.get('label', 'N/A')}: {param.get('name', 'N/A')}")
                return True
            else:
                print("❌ 参数配置格式错误")
                return False
        else:
            print("❌ 没有找到参数配置")
            return False
            
    except Exception as e:
        print(f"❌ 参数配置测试失败: {str(e)}")
        return False

def main():
    """
    主测试函数
    """
    print("🚀 开始测试新闻分析插件...\n")
    
    test_results = {
        'proxy': False,
        'search': False,
        'keywords': False,
        'dedup': False,
        'params': False
    }
    
    # 1. 测试代理连接
    test_results['proxy'] = test_proxy_connection()
    
    # 2. 测试插件参数
    test_results['params'] = test_plugin_parameters()
    
    # 3. 测试新闻搜索
    news_list = test_news_search()
    test_results['search'] = news_list is not None
    
    # 4. 测试关键词分析
    if news_list:
        keywords = test_keyword_analysis(news_list)
        test_results['keywords'] = keywords is not None
    
    # 5. 测试去重功能
    test_results['dedup'] = test_deduplication()
    
    # 输出测试结果
    print("\n" + "="*50)
    print("📊 测试结果汇总:")
    print("="*50)
    
    for test_name, result in test_results.items():
        status = "✅ 通过" if result else "❌ 失败"
        test_names = {
            'proxy': '代理连接',
            'search': '新闻搜索',
            'keywords': '关键词分析',
            'dedup': '去重功能',
            'params': '参数配置'
        }
        print(f"{test_names[test_name]}: {status}")
    
    passed_count = sum(test_results.values())
    total_count = len(test_results)
    
    print(f"\n总体结果: {passed_count}/{total_count} 项测试通过")
    
    if passed_count == total_count:
        print("🎉 所有测试通过！插件功能正常。")
    else:
        print("⚠️  部分测试失败，请检查相关配置。")

if __name__ == '__main__':
    main()