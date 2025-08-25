import asyncio
import json
import os
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
from langchain_community.callbacks.manager import get_openai_callback
from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from utils.logger import get_logger
from .prompts import LANGGRAPH_MAP_PROMPT, LANGGRAPH_REDUCE_PROMPT

class GraphState(TypedDict):
    """LangGraph状态定义"""
    documents: List[Document]
    map_results: List[str]
    final_result: str
    max_trajectories: int
    error: Optional[str]

@dataclass
class ProcessingConfig:
    """LangChain处理器配置"""
    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_tokens_per_chunk: int = 5000
    max_trajectories_per_chunk: int = 10
    temperature: float = 0.0
    max_retries: int = 3
    request_timeout: int = 60
    min_chunk_length: int = 30  # 最小文档块长度
    total_trajectories_target: int = 40  # 总轨迹数目标

class LangChainProcessor:
    """
    基于LangChain的生平数据处理器
    
    实现智能文档分割、并发LLM处理和结果合并的完整流程。
    相比原始实现，提供更好的文档分割策略、错误处理和可观测性。
    
    主要特性：
    - 智能文档分割（基于语义边界）
    - 并发LLM处理（MapReduce模式）
    - 自动重试和错误恢复
    - 详细的性能监控
    - 结果质量评估
    
    使用示例：
        processor = LangChainProcessor(api_key="your-api-key")
        result = await processor.process_biography(biography_text)
    """
    
    def __init__(self, api_key: Optional[str] = None, config: Optional[ProcessingConfig] = None):
        """
        初始化LangChain处理器
        
        Args:
            api_key: OpenAI API密钥，如果为None则从环境变量获取
            config: 处理器配置，如果为None则使用默认配置
        """
        self.logger = get_logger(self.__class__.__name__)
        self.config = config or ProcessingConfig()
        
        # 初始化OpenAI客户端
        api_key = api_key or os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OpenAI API key is required")
            
        self.llm = ChatOpenAI(
            openai_api_key=api_key,
            model_name="gpt-4.1-mini",
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens_per_chunk,
            request_timeout=self.config.request_timeout,
            max_retries=self.config.max_retries
        )
        
        # 初始化文档分割器
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.chunk_size,
            chunk_overlap=self.config.chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", ";", ":", " ", ""],
            keep_separator=True
        )
        
        # 初始化处理链
        self._setup_chains()
        
        self.logger.info(f"LangChain处理器初始化完成，配置: {self.config}")
    
    def _setup_chains(self) -> None:
        """
        设置LangGraph处理图
        
        构建MapReduce模式的文档处理图：
        1. Map阶段：并发处理每个文档块
        2. Reduce阶段：合并所有处理结果
        """
        # 使用prompts.py中的模板
        self.map_prompt = PromptTemplate(
            template=LANGGRAPH_MAP_PROMPT,
            input_variables=["text", "max_trajectories"]
        )
        
        self.reduce_prompt = PromptTemplate(
            template=LANGGRAPH_REDUCE_PROMPT,
            input_variables=["text"]
        )
        
        # 创建LangGraph工作流
        self._create_graph()
    
    async def process_biography(self, biography_text: str) -> Dict[str, Any]:
        """
        处理人物生平文本，提取轨迹数据和坐标信息
        
        Args:
            biography_text: 人物生平文本
            
        Returns:
            包含life_trajectory的字典
            
        Raises:
            ValueError: 输入文本为空或无效
            Exception: LLM处理失败
        """
        if not biography_text or not biography_text.strip():
            raise ValueError("Biography text cannot be empty")
        
        self.logger.info(f"开始处理生平文本，长度: {len(biography_text)}字符")
        
        try:
            # 1. 智能文档分割
            documents = await self._split_documents(biography_text)
            # 2. 并发处理文档块
            result = await self._process_documents(documents)
            # 3. 验证和清理结果
            validated_result = self._validate_result(result)
            self.logger.info(f"处理完成，生成轨迹点: {len(validated_result.get('life_trajectory', {}).get('trajectory', []))}个")
            return validated_result
            
        except Exception as e:
            self.logger.error(f"处理生平文本失败: {str(e)}")
            raise
    
    async def _split_documents(self, text: str) -> List[Document]:
        """
        智能分割文档
        
        Args:
            text: 原始文本
            
        Returns:
            分割后的文档列表
        """
        # 使用LangChain的智能分割器
        documents = self.text_splitter.create_documents([text])
        
        # 输出每个chunk的详细信息
        self.logger.info(f"文档分割结果: 共生成 {len(documents)} 个chunks")
        for i, doc in enumerate(documents):
            content_preview = doc.page_content
            self.logger.info(f"Chunk {i+1}: 长度={len(doc.page_content)}, 内容预览='{content_preview}'")
        
        # 过滤过短的文档块
        filtered_docs = [
            doc for doc in documents 
            if len(doc.page_content.strip()) >= self.config.min_chunk_length
        ]
        
        self.logger.info(f"文档分割完成: {len(documents)} -> {len(filtered_docs)}块（过滤后）")
        
        # 为每个文档添加元数据
        for i, doc in enumerate(filtered_docs):
            doc.metadata.update({
                "chunk_id": i,
                "chunk_length": len(doc.page_content),
                "max_trajectories": self._calculate_max_trajectories(len(filtered_docs))
            })
        
        return filtered_docs
    
    def _calculate_max_trajectories(self, total_chunks: int) -> int:
        """
        根据文档块数量动态计算每块的最大轨迹数，目前简单平均分配
        
        Args:
            total_chunks: 总文档块数
            
        Returns:
            每块的最大轨迹数
        """
        if total_chunks <= 1:
            return self.config.max_trajectories_per_chunk
        
        # 使用配置的总轨迹数目标，根据块数动态分配
        max_per_chunk = max(1, min(self.config.max_trajectories_per_chunk, self.config.total_trajectories_target // total_chunks))
        self.logger.debug(f"计算轨迹数限制: {total_chunks}块 -> 每块最多{max_per_chunk}个轨迹")
        return max_per_chunk
    
    def _create_graph(self) -> None:
        """
        创建LangGraph工作流图
        """
        # 创建状态图
        workflow = StateGraph(GraphState)
        
        # 添加节点
        workflow.add_node("map_documents", self._map_documents_node)
        workflow.add_node("reduce_results", self._reduce_results_node)
        
        # 设置入口点
        workflow.set_entry_point("map_documents")
        
        # 添加边
        workflow.add_edge("map_documents", "reduce_results")
        workflow.add_edge("reduce_results", END)
        
        # 编译图
        self.graph = workflow.compile()
    
    async def _map_documents_node(self, state: GraphState) -> GraphState:
        """
        Map阶段：并发处理每个文档块
        """
        documents = state["documents"]
        max_trajectories = state["max_trajectories"]
        
        if not documents:
            return {**state, "map_results": [], "error": None}
        
        self.logger.info(f"Map阶段：处理 {len(documents)} 个文档块")
        
        try:
            # 并发处理所有文档
            tasks = []
            for doc in documents:
                task = self._process_single_document(doc, max_trajectories)
                tasks.append(task)
            
            map_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 过滤异常结果
            valid_results = []
            for result in map_results:
                if isinstance(result, Exception):
                    self.logger.warning(f"文档处理失败: {str(result)}")
                else:
                    valid_results.append(result)
            
            return {**state, "map_results": valid_results, "error": None}
            
        except Exception as e:
            self.logger.error(f"Map阶段失败: {str(e)}")
            return {**state, "map_results": [], "error": str(e)}
    
    async def _reduce_results_node(self, state: GraphState) -> GraphState:
        """
        Reduce阶段：合并所有处理结果
        """
        map_results = state["map_results"]
        
        if not map_results:
            empty_result = json.dumps({
                "life_trajectory": {"person_name": "", "trajectory": []}
            })
            return {**state, "final_result": empty_result, "error": None}
        
        self.logger.info(f"Reduce阶段：合并 {len(map_results)} 个结果")
        
        try:
            # 合并所有Map结果
            combined_text = "\n\n".join(map_results)
            
            # 使用LLM进行最终合并
            reduce_input = self.reduce_prompt.format(text=combined_text)
            
            with get_openai_callback() as cb:
                final_result = await asyncio.to_thread(
                    self.llm.invoke,
                    reduce_input
                )
                
                self.logger.info(
                    f"Reduce阶段完成 - Token使用: {cb.total_tokens}, "
                    f"成本: ${cb.total_cost:.4f}, 请求次数: {cb.successful_requests}"
                )
            
            # 提取文本内容
            if hasattr(final_result, 'content'):
                result_text = final_result.content
            else:
                result_text = str(final_result)
            return {**state, "final_result": result_text, "error": None}
            
        except Exception as e:
            self.logger.error(f"Reduce阶段失败: {str(e)}")
            return {**state, "final_result": "", "error": str(e)}
    
    async def _process_single_document(self, doc: Document, max_trajectories: int) -> str:
        """
        处理单个文档块
        
        Args:
            doc: 文档对象
            max_trajectories: 最大轨迹数
            
        Returns:
            处理结果字符串
        """
        # 格式化prompt
        map_input = self.map_prompt.format(
            text=doc.page_content,
            max_trajectories=max_trajectories
        )
        # 调用LLM
        result = await asyncio.to_thread(self.llm.invoke, map_input)
        # 提取文本内容
        return result.content if hasattr(result, 'content') else str(result)
    
    async def _process_documents(self, documents: List[Document]) -> Dict[str, Any]:
        """
        使用LangGraph处理文档块
        
        Args:
            documents: 文档列表
            
        Returns:
            处理结果
        """
        if not documents:
            return {"life_trajectory": {"person_name": "", "trajectory": []}, "coordinates": []}
        
        self.logger.info(f"开始使用LangGraph处理 {len(documents)} 个文档块")
        
        # 准备初始状态
        initial_state: GraphState = {
            "documents": documents,
            "map_results": [],
            "final_result": "",
            "max_trajectories": documents[0].metadata.get("max_trajectories", self.config.max_trajectories_per_chunk),
            "error": None
        }
        
        try:
            # 执行图工作流 - 使用异步API
            final_state = await self.graph.ainvoke(initial_state)
            
            # 检查是否有错误
            if final_state.get("error"):
                raise Exception(f"LangGraph处理失败: {final_state['error']}")
            
            # 解析最终结果
            result = self._parse_result(final_state["final_result"])
            
            self.logger.info("LangGraph处理完成")
            return result
            
        except Exception as e:
            self.logger.error(f"LangGraph处理失败: {str(e)}")
            raise
    
    def _parse_result(self, raw_result: str) -> Dict[str, Any]:
        """
        解析LLM返回的结果
        
        Args:
            raw_result: LLM原始返回结果
            
        Returns:
            解析后的结构化数据
        """
        try:
            # 清理markdown代码块标记
            if isinstance(raw_result, str):
                # 移除可能的markdown代码块标记
                cleaned_result = raw_result.strip()
                if cleaned_result.startswith('```json'):
                    cleaned_result = cleaned_result[7:]  # 移除```json
                if cleaned_result.startswith('```'):
                    cleaned_result = cleaned_result[3:]  # 移除```
                if cleaned_result.endswith('```'):
                    cleaned_result = cleaned_result[:-3]  # 移除结尾的```
                cleaned_result = cleaned_result.strip()
            else:
                cleaned_result = raw_result
            
            # 解析JSON
            result = json.loads(cleaned_result) if isinstance(cleaned_result, str) else cleaned_result
            
            # 标准化结果格式
            if "life_trajectory" not in result and "person_name" in result:
                # 转换为标准格式
                result = {
                    "life_trajectory": {
                        "person_name": result.get("person_name", ""),
                        "trajectory": result.get("trajectory", [])
                    }
                }
            
            return result
            
        except (json.JSONDecodeError, TypeError) as e:
            self.logger.warning(f"解析LLM结果失败: {str(e)}, 原始结果: {raw_result[:200]}...")
            return {
                "life_trajectory": {"person_name": "", "trajectory": []}
            }
    
    def _validate_result(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """
        验证和清理处理结果，目前简单根据时间与地点去重，后续可使用LLM
        
        Args:
            result: 原始结果
            
        Returns:
            验证后的结果
        """
        # 确保基本结构存在
        if "life_trajectory" not in result:
            result["life_trajectory"] = {"person_name": "", "trajectory": []}
        
        # 验证轨迹数据
        trajectory = result["life_trajectory"].get("trajectory", [])
        if isinstance(trajectory, list):
            # 去重和排序
            unique_trajectory = self._deduplicate_data(
                trajectory, 
                ["time", "location"]
            )
            result["life_trajectory"]["trajectory"] = unique_trajectory
        
        return result
    
    def _deduplicate_data(self, data: List[Dict], key_fields: List[str], sort_key: Optional[str] = None) -> List[Dict]:
        """
        通用去重方法
        
        Args:
            data: 待去重的数据列表
            key_fields: 用于创建唯一标识的字段列表
            sort_key: 排序字段（可选）
            
        Returns:
            去重后的数据列表
        """
        seen = set()
        unique_data = []
        
        for item in data:
            if not isinstance(item, dict):
                continue
                
            # 创建唯一标识
            key = tuple(item.get(field, "") for field in key_fields)
            
            if key not in seen:
                seen.add(key)
                unique_data.append(item)
        
        # 按指定字段排序（如果提供）
        if sort_key:
            try:
                unique_data.sort(key=lambda x: x.get(sort_key, ""))
            except (TypeError, ValueError):
                pass  # 如果排序失败，保持原顺序
        
        return unique_data

    async def close(self) -> None:
        """
        清理资源
        """
        self.logger.info("LangChain处理器资源清理完成")