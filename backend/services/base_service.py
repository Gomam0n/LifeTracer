# -*- coding: utf-8 -*-
"""
Base service class with common functionality
"""
import aiohttp
from abc import ABC
from utils.logger import LoggerMixin
from typing import Optional


class BaseService(LoggerMixin, ABC):
    """
    Base service class providing common functionality like session management
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def get_session(self) -> aiohttp.ClientSession:
        """
        Get or create HTTP session
        """
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)  # 30 second timeout
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def close(self):
        """
        Clean up resources
        """
        if self.session:
            await self.session.close()
            self.session = None
    
    async def __aenter__(self):
        """Async context manager entry"""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        await self.close()