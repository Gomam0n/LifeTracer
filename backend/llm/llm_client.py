"""
简单的GPT模型交互客户端
"""
import aiohttp
import asyncio
from typing import Optional, List, Dict, Any


class LLMClient:
    def __init__(self, api_key: str, base_url: str = "https://api.openai.com/v1", model: str = "gpt-4.1-mini"):
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.session = None
    
    async def _get_session(self):
        """获取HTTP会话"""
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        """关闭客户端"""
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def chat(self, message: str, system_prompt: Optional[str] = None, max_tokens: int = 10000, temperature: float = 0.0) -> str:
        session = await self._get_session()
        
        # 构建消息
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": message})
        
        # 构建请求数据
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        url = f"{self.base_url}/chat/completions"
        
        try:
            async with session.post(url, json=data, headers=headers) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API错误 {response.status}: {error_text}")
                
                result = await response.json()
                return result["choices"][0]["message"]["content"]
        except Exception as e:
            raise Exception(f"GPT请求失败: {str(e)}")
    
    async def chat_batch(self, requests: List[Dict[str, Any]]) -> List[str]:
        """
        批量并发处理多个LLM请求
        
        Args:
            requests: 请求列表，每个请求包含 {"message": str, "system_prompt": str, "max_tokens": int, "temperature": float}
            
        Returns:
            响应列表，与请求顺序对应
        """
        import time
        from utils.logger import get_logger
        
        logger = get_logger("LLMClient")
        
        async def timed_chat(req_index: int, req: Dict[str, Any]):
            """带时间记录的chat请求"""
            start_time = time.time()
            try:
                result = await self.chat(
                    message=req["message"],
                    system_prompt=req.get("system_prompt"),
                    max_tokens=req.get("max_tokens", 10000),
                    temperature=req.get("temperature", 0.0)
                )
                end_time = time.time()
                duration = end_time - start_time
                logger.info(f"Chat请求#{req_index+1} 耗时: {duration:.2f}秒")
                # logger.info(f"Chat请求#{req_index+1} 输入: {req['message']}")
                # logger.info(f"Chat请求#{req_index+1} 输出: {result}")

                return result
            except Exception as e:
                end_time = time.time()
                duration = end_time - start_time
                logger.error(f"Chat请求#{req_index+1} 失败，耗时: {duration:.2f}秒，错误: {str(e)}")
                raise e
        
        tasks = []
        for i, req in enumerate(requests):
            task = timed_chat(i, req)
            tasks.append(task)
        
        # 并发执行所有请求
        batch_start_time = time.time()
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            batch_end_time = time.time()
            batch_duration = batch_end_time - batch_start_time
            logger.info(f"批量请求总耗时: {batch_duration:.2f}秒，请求数: {len(requests)}")

            # 处理异常结果
            processed_results = []
            for i, result in enumerate(results):
                if isinstance(result, Exception):
                    raise Exception(f"批量请求第{i+1}个失败: {str(result)}")
                processed_results.append(result)
            
            return processed_results
        except Exception as e:
            batch_end_time = time.time()
            batch_duration = batch_end_time - batch_start_time
            logger.error(f"批量LLM请求失败，总耗时: {batch_duration:.2f}秒，错误: {str(e)}")
            raise Exception(f"批量LLM请求失败: {str(e)}")

