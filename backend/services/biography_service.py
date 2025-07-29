# -*- coding: utf-8 -*-
import asyncio
import aiohttp
from typing import Dict, List, Any
import json
from bs4 import BeautifulSoup
import sys
import os
# 添加backend目录到Python路径
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from models.response_models import BiographyData
from utils.cache_manager import CacheManager
from utils.llm_client import LLMClient
from utils.logger import get_logger
from utils.prompts import CITY_COORDINATES_PROMPT, LIFE_TRAJECTORY_PROMPT

logger = get_logger(__name__)

class BiographyService:
    def __init__(self):
        self.cache = CacheManager()
        self.llm_client = LLMClient(os.environ.get("OPENAI_API_KEY"))
        self.session = None
        
    async def get_session(self):
        if self.session is None:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session:
            await self.session.close()
    
    async def get_biography(self, name: str, language: str = "zh-hans", detail_level: str = "medium") -> BiographyData:
        """
        获取历史人物的生平信息
        """
        # 检查缓存
        cache_key = f"biography_{name}_{language}_{detail_level}"
        cached_data = await self.cache.get(cache_key)
        if cached_data:
            logger.info(f"从缓存获取 {name} 的生平信息")
            return BiographyData(**cached_data)
        
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
            
            logger.info(f"成功获取 {name} 的生平信息")
            return biography
            
        except Exception as e:
            logger.error(f"获取 {name} 生平信息失败: {str(e)}")
            raise Exception(f"无法获取 {name} 的生平信息: {str(e)}")
    
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
                "srlimit": 5
            }
            
            logger.debug(f"正在搜索维基百科: {name}")
            logger.debug(f"搜索URL: {search_url}")
            logger.debug(f"搜索参数: {search_params}")
            
            async with session.get(search_url, params=search_params) as response:
                search_data = await response.json()
            
            logger.debug(f"搜索结果: {json.dumps(search_data, ensure_ascii=False, indent=2)}")
            
            if not search_data.get("query", {}).get("search"):
                raise Exception(f"在维基百科中未找到 {name} 的相关信息")
            
            # 获取最相关的页面标题
            page_title = search_data["query"]["search"][0]["title"]
            logger.debug(f"找到页面: {page_title}")
            
            # 2. 获取页面内容
            content_params = {
                "action": "parse",
                "format": "json",
                "page": page_title,
                "prop": "sections|text",
            }
            
            logger.debug(f"获取页面内容参数: {content_params}")
            
            async with session.get(search_url, params=content_params) as response:
                content_data = await response.json()     

            html_text = content_data["parse"]["text"]
            if isinstance(html_text, dict) and "*" in html_text:
                html_content = html_text["*"]
            elif isinstance(html_text, str):
                html_content = html_text
            else:
                logger.debug(f"意外的text类型: {type(html_text)}")
                html_content = str(html_text)
            biography_section = self.extract_h2_section_content(html_content, "生平")
            if not biography_section:
                return html_content
            return biography_section
            
        except Exception as e:
            logger.error(f"从维基百科获取 {name} 信息失败: {str(e)}")
            raise

    def extract_h2_section_content(self, html_content: str, target_h2_id: str) -> str:
        """
        从HTML内容中提取指定h2标签到下一个h2标签之间的内容
        
        Args:
            html_content: HTML内容字符串
            target_h2_id: 目标h2标签的id属性值（如"生平"）
        
        Returns:
            提取的内容文本，如果未找到则返回空字符串
        """
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 查找目标h2标签，可能被包装在div中
            target_h2 = soup.find('h2', {'id': target_h2_id})
            if not target_h2:
                logger.debug(f"未找到id为'{target_h2_id}'的h2标签")
                return ""
            
            logger.debug(f"找到目标h2标签: {target_h2.get_text()}")
            
            # 找到h2标签的父容器（可能是div）
            h2_container = target_h2.parent
            logger.debug(f"h2容器标签: {h2_container.name if h2_container else 'None'}")
            
            # 收集从h2容器之后到下一个h2容器之间的所有内容
            content_elements = []
            current_element = h2_container.next_sibling if h2_container else target_h2.next_sibling
            
            while current_element:
                # 检查是否遇到下一个h2标签（可能在div中或直接的h2）
                if current_element.name == 'h2':
                    logger.debug(f"遇到下一个h2标签: {current_element.get_text()}")
                    break
                elif current_element.name == 'div' and current_element.find('h2'):
                    # 检查div中是否包含h2标签
                    next_h2 = current_element.find('h2')
                    logger.debug(f"遇到包含h2的div: {next_h2.get_text()}")
                    break
                
                # 收集有效的内容元素
                if current_element.name and current_element.name not in ['script', 'style', 'meta']:
                    content_elements.append(current_element)
                
                current_element = current_element.next_sibling
                logger.debug(current_element)
            
            # 提取文本内容
            extracted_text = ""
            for element in content_elements:
                if element.name in ['p', 'div', 'ul', 'ol', 'li', 'table', 'blockquote']:
                    # 跳过包含h2的div（这些是章节标题）
                    if element.name == 'div' and element.find('h2'):
                        continue
                    
                    text = element.get_text(strip=True)
                    if text:
                        extracted_text += text + "\n\n"
            
            logger.debug(f"提取的内容长度: {len(extracted_text)}")
            logger.debug(f"内容预览: {extracted_text[:200]}...")
            
            return extracted_text.strip()
            
        except Exception as e:
            logger.debug(f"提取h2章节内容失败: {str(e)}")
            return ""
    
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
            logger.error(f"搜索建议失败: {str(e)}")
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

# 测试函数
async def test_wikipedia_api():
    """测试维基百科API请求"""
    service = BiographyService()
    
    try:
        logger.info("=== 测试维基百科API ===")
        # 测试搜索功能
        suggestions = await service.search_suggestions("苏轼")
        logger.info(f"搜索建议: {suggestions}")
        
        # 测试获取维基百科数据
        wiki_data = await service._get_wikipedia_data("苏轼", "zh")
        logger.info(f"维基百科数据获取成功")
        
    except Exception as e:
        logger.error(f"维基百科API测试失败: {e}")
    finally:
        await service.close()


async def test_llm_enhancement():
    """测试LLM增强功能"""
    service = BiographyService()
    
    try:
        logger.info("\n=== 测试LLM增强 ===")
        # 模拟维基百科数据
        mock_wiki_data = {
            "title": "李白",
            "extract": "李白（701年－762年），字太白，号青莲居士，唐朝浪漫主义诗人，被后人誉为`诗仙`。",
            "full_content": "李白（701年－762年），字太白，号青莲居士，唐朝浪漫主义诗人，被后人誉为`诗仙`。祖籍陇西成纪，出生于中亚西域的碎叶城，后来随父亲迁至剑南道绵州。李白存世诗文千余篇，有《李太白集》传世。代表作有《望庐山瀑布》、《行路难》、《蜀道难》、《将进酒》、《梁甫吟》、《早发白帝城》等多首。",
            "url": "https://zh.wikipedia.org/wiki/李白"
        }
        
        enhanced_data = await service._enhance_with_llm(mock_wiki_data, "medium")
        logger.info(f"LLM增强成功: {json.dumps(enhanced_data, ensure_ascii=False, indent=2)}")
        
    except Exception as e:
        logger.error(f"LLM增强测试失败: {e}")
    finally:
        await service.close()


async def test_full_biography():
    """测试完整的传记获取流程"""
    service = BiographyService()
    
    try:
        logger.info("\n=== 测试完整传记获取 ===")
        biography = await service.get_biography("李白", "zh", "medium")
        logger.info(biography)
    except Exception as e:
        logger.error(f"完整传记测试失败: {e}")
    finally:
        await service.close()



if __name__ == "__main__":
    logger.info("BiographyService 测试程序")
    
    choice = "1"
    
    if choice == "1":
        asyncio.run(test_full_biography())