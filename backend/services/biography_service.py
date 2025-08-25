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
from llm.prompts import CITY_COORDINATES_PROMPT, LIFE_TRAJECTORY_PROMPT, LIFE_TRAJECTORY_WITH_COORDINATES_PROMPT
from .base_service import BaseService
from utils.error_handler import handle_service_error, WikipediaError, LLMError, log_and_raise_error
from utils.html_parser import HTMLParser

from llm.langchain_processor import LangChainProcessor, ProcessingConfig

class BiographyService(BaseService):
    # 静态类变量：短段落合并的最小字符数阈值
    MIN_PARAGRAPH_LENGTH = 200
    
    def __init__(self):
        super().__init__()
        # 使用缓存工厂，支持动态选择文件缓存或Redis缓存
        # 通过环境变量 CACHE_TYPE 或 REDIS_URL 控制
        self.cache = get_cache_manager()
        self.llm_client = LLMClient(os.environ.get("OPENAI_API_KEY"))
        # 请求去重锁字典，防止并发请求同一人物时重复调用API
        self._request_locks = {}
        
        # 初始化LangChain处理器
        try:
            self._langchain_processor = LangChainProcessor(
                api_key=os.environ.get("OPENAI_API_KEY")
            )
            self.logger.info("LangChain处理器初始化成功")
        except Exception as e:
            self.logger.warning(f"LangChain处理器初始化失败: {str(e)}")
            self._langchain_processor = None
    
    async def close(self):
        """Override parent close to also clear locks"""
        await super().close()
        # 清理所有锁
        self._request_locks.clear()
        # 清理LangChain处理器
        if self._langchain_processor:
            await self._langchain_processor.close()
            self._langchain_processor = None
    
    # 为了简化代码和避免竞态条件，我们不主动清理锁对象
    @handle_service_error
    async def get_biography(self, name: str, language: str = "zh-hans", detail_level: str = "medium", parse_mode: int = 3) -> BiographyData:
        """
        获取历史人物的生平信息
        使用请求去重机制防止并发请求造成重复API调用
        
        Args:
            name: 人物姓名
            language: 语言设置
            detail_level: 详细程度
            parse_mode: 解析模式
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
                self.logger.info(f"获取维基百科数据成功")

                # 2. 根据parse_mode选择不同的解析策略
                if parse_mode == 1:
                    # 模式1：串行调用（1+N次请求）
                    trajectory_data = await self._parse_mode_1(wiki_data)
                elif parse_mode == 2:
                    # 模式2：合并调用（1次请求）
                    trajectory_data = await self._parse_mode_2(wiki_data)
                elif parse_mode == 3:
                    # 模式3：并发调用（基于自然段分隔）
                    trajectory_data = await self._parse_mode_3(wiki_data)
                elif parse_mode == 4:
                    # 模式4：LangChain智能解析
                    trajectory_data = await self._parse_mode_4(wiki_data)
                else:
                    raise ValueError(f"不支持的parse_mode: {parse_mode}")
                
                self.logger.info(f"使用模式{parse_mode}解析完成")
                
                # 3. 处理返回的数据
                coordinates = []
                descriptions = []
                
                for trajectory in trajectory_data["trajectory"]:
                    # 提取坐标信息
                    coords = trajectory["coordinates"]
                    coordinates.append([coords["longitude"], coords["latitude"]])
                    # 提取描述信息
                    descriptions.append(trajectory["time"] + "," + trajectory["description"])
                
                biography = BiographyData(
                    name=name,
                    coordinates=coordinates,
                    descriptions=descriptions
                )
                self.logger.info(f"数据处理完成")
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

    async def extract_life_trajectory_with_coordinates(self, biography_text: str) -> Dict[str, Any]:
        """
        从人物生平信息中一次性提取轨迹信息和坐标（性能优化版本）
        
        Args:
            biography_text: 人物生平文本
            
        Returns:
            包含轨迹信息和坐标的字典
        """
        user_prompt = f"请分析以下人物生平信息，提取轨迹数据和坐标信息：\n\n{biography_text}"
        
        try:
            response = await self.llm_client.chat(
                message=user_prompt,
                system_prompt=LIFE_TRAJECTORY_WITH_COORDINATES_PROMPT
            )
            trajectory_data = json.loads(response)
            return trajectory_data
        except Exception as e:
            raise Exception(f"提取轨迹和坐标信息失败: {str(e)}")

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

    async def _parse_mode_1(self, biography_text: str) -> Dict[str, Any]:
        """
        模式1：串行调用（1+N次请求）
        先解析生平，再逐个解析地点坐标
        """
        # 第一步：提取轨迹信息
        trajectory_data = await self.extract_life_trajectory(biography_text)
        
        # 第二步：逐个获取地点坐标
        for trajectory in trajectory_data["trajectory"]:
            place = trajectory.get("place", "")
            if place:
                # 为每个地点单独调用LLM获取坐标
                coord_response = await self.get_city_coordinates([place])
                if coord_response and len(coord_response) > 0:
                    coords = coord_response[0]
                    trajectory["coordinates"] = {
                        "longitude": coords.get("longitude", 0),
                        "latitude": coords.get("latitude", 0)
                    }
                else:
                    trajectory["coordinates"] = {"longitude": 0, "latitude": 0}
            else:
                trajectory["coordinates"] = {"longitude": 0, "latitude": 0}
        
        return trajectory_data

    async def _parse_mode_2(self, biography_text: str) -> Dict[str, Any]:
        """
        模式2：合并调用（1次请求）
        一次性解析所有生平及地点坐标
        """
        return await self.extract_life_trajectory_with_coordinates(biography_text)

    async def _parse_mode_3(self, biography_text: str) -> Dict[str, Any]:
        """
        模式3：并发调用（基于自然段分隔）
        将生平数据按自然段分隔，并发调用LLM解析
        """
        # 按自然段（空行）分隔文本
        raw_paragraphs = [p.strip() for p in biography_text.split('\n\n') if p.strip()]
        
        if not raw_paragraphs:
            # 如果没有自然段分隔，回退到模式2
            return await self._parse_mode_2(biography_text)
        
        # 合并较短的段落
        paragraphs = self._merge_short_paragraphs(raw_paragraphs)
        
        self.logger.info(f"原始段落数: {len(raw_paragraphs)}, 合并后段落数: {len(paragraphs)}")
        
        # 根据段落数量动态计算每段轨迹数量限制
        max_trajectories_per_paragraph = max(1, min(10, 30 // len(paragraphs)))
        
        # 为每个段落创建prompt
        prompts = []
        for i, paragraph in enumerate(paragraphs):
            # 在原始prompt基础上添加轨迹数量限制规则
            enhanced_prompt = LIFE_TRAJECTORY_WITH_COORDINATES_PROMPT + f"\n\n重要规则：由于这是分段解析，请严格控制输出的轨迹点数量不超过{max_trajectories_per_paragraph}个，优先选择最重要的轨迹点。"
            
            prompt = f"请分析以下人物生平片段，提取轨迹数据和坐标信息（段落{i+1}）：\n\n{paragraph}"
            prompts.append({
                "message": prompt,
                "system_prompt": enhanced_prompt
            })

        
        # 并发调用LLM
        responses = await self.llm_client.chat_batch(prompts)
        
        self.logger.info(f"LLM响应数: {len(responses)}")

        # 合并所有响应结果
        merged_trajectory = {
            "person_name": "",
            "trajectory": []
        }

        for response in responses:
            try:
                if response:
                    data = json.loads(response)
                    if not merged_trajectory["person_name"] and data.get("person_name"):
                        merged_trajectory["person_name"] = data["person_name"]
                    
                    if "trajectory" in data and isinstance(data["trajectory"], list):
                        merged_trajectory["trajectory"].extend(data["trajectory"])
            except (json.JSONDecodeError, TypeError) as e:
                self.logger.warning(f"解析段落响应失败: {str(e)}")
                continue
        
        # 如果没有获取到人名，使用原始输入
        if not merged_trajectory["person_name"]:
            merged_trajectory["person_name"] = 'Unknown'
        
        return merged_trajectory
    
    async def _parse_mode_4(self, wiki_data: str) -> Dict[str, Any]:
        """
        模式4：使用LangChain智能解析
        利用LangChain框架进行智能文档分割、并发处理和结果合并
        
        Args:
            wiki_data: Wikipedia文本数据
            
        Returns:
            包含trajectory的字典
        """
        if not self._langchain_processor:
            self.logger.warning("LangChain处理器未初始化，回退到模式3")
            return await self._parse_mode_3(wiki_data)
            
        try:
            self.logger.info("开始使用LangChain模式4处理生平数据")
            
            # 使用LangChain处理器处理文档
            result = await self._langchain_processor.process_biography(wiki_data)
            
            # 验证结果格式
            if not isinstance(result, dict):
                raise ValueError("LangChain处理器返回格式错误")
            self.logger.info(result)
            # 提取LangChain处理器返回的数据结构
            life_trajectory_data = result.get('life_trajectory', {})
            
            # 从嵌套结构中提取轨迹数据
            if isinstance(life_trajectory_data, dict):
                trajectory = life_trajectory_data.get('trajectory', [])
                person_name = life_trajectory_data.get('person_name', 'Unknown')
            else:
                trajectory = []
                person_name = 'Unknown'
            
            # 验证数据完整性
            if not trajectory:
                self.logger.warning("LangChain处理未返回生平轨迹，回退到模式3")
                return await self._parse_mode_3(wiki_data)
                
            # 构建与其他模式一致的返回格式
            merged_trajectory = {
                'person_name': person_name,
                'trajectory': trajectory
            }
                
            self.logger.info(f"LangChain模式4处理完成，提取到{len(trajectory)}个轨迹点")
            
            return merged_trajectory
            
        except Exception as e:
            self.logger.error(f"LangChain模式4处理失败: {str(e)}，回退到模式3")
            # 出现错误时回退到模式3
            return await self._parse_mode_3(wiki_data)
    
    def _merge_short_paragraphs(self, paragraphs: List[str]) -> List[str]:
        """
        合并较短的段落与后一段
        
        Args:
            paragraphs: 原始段落列表
            
        Returns:
            合并后的段落列表
        """
        if not paragraphs:
            return paragraphs
            
        merged = []
        i = 0
        
        while i < len(paragraphs):
            current_paragraph = paragraphs[i]
            
            # 如果当前段落较短且不是最后一段，则与下一段合并
            if (len(current_paragraph) < self.MIN_PARAGRAPH_LENGTH and 
                i < len(paragraphs) - 1):
                # 与下一段合并
                next_paragraph = paragraphs[i + 1]
                merged_paragraph = current_paragraph + "\n\n" + next_paragraph
                merged.append(merged_paragraph)
                i += 2  # 跳过下一段，因为已经合并了
            else:
                # 段落足够长或是最后一段，直接添加
                merged.append(current_paragraph)
                i += 1
                
        return merged
