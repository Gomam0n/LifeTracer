# -*- coding: utf-8 -*-
import asyncio
from typing import Dict, List, Any
import json
import sys
import os
# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models.response_models import BiographyData
from caching.cache_factory import get_cache_manager
from llm.llm_client import LLMClient
from llm.prompts import CITY_COORDINATES_PROMPT, LIFE_TRAJECTORY_PROMPT
from .base_service import BaseService
from utils.error_handler import handle_service_error, WikipediaError, LLMError, log_and_raise_error
from utils.html_parser import HTMLParser

class BiographyService(BaseService):
    def __init__(self):
        super().__init__()
        # 使用缓存工厂，支持动态选择文件缓存或Redis缓存
        # 通过环境变量 CACHE_TYPE 或 REDIS_URL 控制
        self.cache = get_cache_manager()
        self.llm_client = LLMClient(os.environ.get("OPENAI_API_KEY"))
        # 请求去重锁字典，防止并发请求同一人物时重复调用API
        self._request_locks = {}
    
    async def close(self):
        """Override parent close to also clear locks"""
        await super().close()
        # 清理所有锁
        self._request_locks.clear()
    
    # 为了简化代码和避免竞态条件，我们不主动清理锁对象
    @handle_service_error
    async def get_biography(self, name: str, language: str = "zh-hans", detail_level: str = "medium") -> BiographyData:
        """
        获取历史人物的生平信息
        使用请求去重机制防止并发请求造成重复API调用
        """
        cache_key = f"biography_{name}_{language}_{detail_level}"
        
        # 第一次检查缓存
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            self.logger.info(f"从缓存获取 {name} 的生平信息")
            return BiographyData(**cached_data)
        
        # 获取或创建该缓存键的锁（原子操作，避免竞态条件）
        lock = self._request_locks.setdefault(cache_key, asyncio.Lock())
        
        # 使用锁确保同一时间只有一个请求在处理
        async with lock:
            # 再次检查缓存（可能在等待锁的过程中其他请求已经完成并缓存了结果）
            cached_data = await self.cache.get(cache_key)
            if cached_data:
                self.logger.info(f"等待期间从缓存获取 {name} 的生平信息")
                return BiographyData(**cached_data)
            
            # 执行实际的数据获取逻辑
            self.logger.info(f"开始处理 {name} 的生平信息请求")
            try:
                # 1. 从维基百科获取基础信息
                wiki_data = await self._get_wikipedia_data(name, language)
                # 2. 使用LLM解析生平
                life_trajectory = await self.extract_life_trajectory(wiki_data)

                name = life_trajectory["person_name"]
                places = []
                descriptions = []
                for trajectory in life_trajectory["trajectory"]:
                    places.append(trajectory["location"])
                    descriptions.append(trajectory["time"] + "," + trajectory["description"])
                
                location_data = await self.get_city_coordinates(places)
                coordinates = []
                for coordinate in location_data["locations"]:
                    coordinates.append([coordinate["longitude"], coordinate["latitude"]])
                biography = BiographyData(
                    name=name,
                    coordinates=coordinates,
                    descriptions=descriptions
                )
                # 4. 缓存结果
                await self.cache.set(cache_key, biography.dict(), expire=3600*24)  # 缓存24小时
                
                self.logger.info(f"成功获取并缓存 {name} 的生平信息")
                return biography
                
            except Exception as e:
                log_and_raise_error(
                    error_type=LLMError,
                    message=f"无法获取 {name} 的生平信息",
                    error_code="BIOGRAPHY_EXTRACTION_FAILED",
                    original_exception=e,
                    details={"name": name, "language": language, "detail_level": detail_level}
                )
    
    async def _get_wikipedia_data(self, name: str, language: str) -> Dict[str, Any]:
        """
        从维基百科获取人物信息
        """
        session = await self.get_session()
        
        # 根据语言选择维基百科域名
        wiki_domain = "zh.wikipedia.org" if language == "zh" else "en.wikipedia.org"
        
        try:
            # 1. 搜索页面
            search_url = f"https://{wiki_domain}/w/api.php"
            search_params = {
                "action": "query",
                "format": "json",
                "list": "search",
                "srsearch": name,
                "srlimit": 5,
                "variant": language == "zh" and "zh-hans" or language
            }
            
            self.logger.debug(f"正在搜索维基百科: {name}")
            self.logger.debug(f"搜索URL: {search_url}")
            self.logger.debug(f"搜索参数: {search_params}")
            
            async with session.get(search_url, params=search_params) as response:
                search_data = await response.json()
            
            self.logger.debug(f"搜索结果: {json.dumps(search_data, ensure_ascii=False, indent=2)}")
            
            if not search_data.get("query", {}).get("search"):
                log_and_raise_error(
                    error_type=WikipediaError,
                    message=f"在维基百科中未找到 {name} 的相关信息",
                    error_code="NO_SEARCH_RESULTS",
                    details={"name": name, "language": language}
                )
            
            # 获取最相关的页面标题
            page_title = search_data["query"]["search"][0]["title"]
            self.logger.debug(f"找到页面: {page_title}")
            
            # 2. 获取页面内容
            content_params = {
                "action": "parse",
                "format": "json",
                "page": page_title,
                "prop": "sections|text",
            }
            
            self.logger.debug(f"获取页面内容参数: {content_params}")
            
            async with session.get(search_url, params=content_params) as response:
                content_data = await response.json()     

            html_text = content_data["parse"]["text"]
            if isinstance(html_text, dict) and "*" in html_text:
                html_content = html_text["*"]
            elif isinstance(html_text, str):
                html_content = html_text
            else:
                self.logger.debug(f"意外的text类型: {type(html_text)}")
                html_content = str(html_text)
            
            # Try to extract biography section, fallback to full content
            biography_section = HTMLParser.extract_section_by_id(html_content, "生平")
            if not biography_section:
                # If no specific biography section, extract all readable text
                biography_section = HTMLParser.extract_all_text(html_content)
            
            return biography_section if biography_section else html_content
            
        except Exception as e:
            log_and_raise_error(
                error_type=WikipediaError,
                message=f"从维基百科获取 {name} 信息失败",
                error_code="WIKIPEDIA_API_ERROR", 
                original_exception=e,
                details={"name": name, "language": language, "wiki_domain": wiki_domain}
            )

    
    async def search_suggestions(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索建议（自动补全功能）
        """
        session = await self.get_session()
        
        try:
            search_url = "https://zh.wikipedia.org/w/api.php"
            params = {
                "action": "opensearch",
                "format": "json",
                "search": query,
                "limit": limit
            }
            
            async with session.get(search_url, params=params) as response:
                data = await response.json()
            
            suggestions = []
            if len(data) >= 2:
                titles = data[1]
                descriptions = data[2] if len(data) > 2 else []
                
                for i, title in enumerate(titles):
                    suggestions.append({
                        "name": title,
                        "description": descriptions[i] if i < len(descriptions) else "",
                        "popularity": 1.0 - (i * 0.1)  # 简单的流行度计算
                    })
            
            return suggestions
            
        except Exception as e:
            self.logger.error(f"搜索建议失败: {str(e)}")
            return []
    
    async def extract_life_trajectory(self, biography_text: str) -> str:
        """
        从人物生平信息中提取轨迹信息
        
        Args:
            biography_text: 人物生平文本
            api_key: OpenAI API密钥
            base_url: API基础URL
            
        Returns:
            包含轨迹信息的JSON字符串
        """
        user_prompt = f"请分析以下人物生平信息，提取轨迹数据：\n\n{biography_text}"
        
        try:
            response = await self.llm_client.chat(
                message=user_prompt,
                system_prompt=LIFE_TRAJECTORY_PROMPT
            )
            trajectory_data = json.loads(response)
            return trajectory_data
        except Exception as e:
            raise Exception(f"提取轨迹信息失败: {str(e)}")

    async def get_city_coordinates(self, places: List[str]) -> str:
        # 将places列表中的元素用逗号分隔
        places_str = "、".join(places)
        user_prompt = f"请提供以下城市或地点的坐标信息：{places_str}"
        
        response = await self.llm_client.chat(
            message=user_prompt,
            system_prompt=CITY_COORDINATES_PROMPT
        )
        coord_data = json.loads(response)
        return coord_data
