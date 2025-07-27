"""
简单的GPT模型交互客户端
"""
import aiohttp
from typing import Optional


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

