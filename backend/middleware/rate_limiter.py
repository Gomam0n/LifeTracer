# -*- coding: utf-8 -*-
"""
Rate Limiter Middleware for LifeTracer
实现基于IP的请求频率限制
"""

import time
from typing import Dict, Tuple
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from utils.logger import get_logger

logger = get_logger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """
    基于IP的请求频率限制中间件
    
    Features:
    - IP级别限制：每个IP独立计算请求频率
    - 滑动窗口：使用时间戳记录，自动清理过期记录
    - 响应头：返回限制信息给客户端
    - 自动清理：定期清理过期的IP记录
    """
    
    def __init__(
        self, 
        app,
        requests_per_minute: int = 30,
        cleanup_interval: int = 300  # 5分钟清理一次
    ):
        """
        初始化速率限制器
        
        Args:
            app: FastAPI应用实例
            requests_per_minute: 每分钟允许的请求数
            cleanup_interval: 清理过期记录的间隔（秒）
        """
        super().__init__(app)
        self.requests_per_minute = requests_per_minute
        self.window_size = 60  # 1分钟窗口
        self.cleanup_interval = cleanup_interval
        
        # 存储每个IP的请求时间戳
        # 格式: {ip: [timestamp1, timestamp2, ...]}
        self.ip_requests: Dict[str, list] = {}
        self.last_cleanup = time.time()
        
        logger.info(f"Rate limiter initialized: {requests_per_minute} requests/minute")
    
    def _get_client_ip(self, request: Request) -> str:
        """
        获取客户端真实IP地址
        考虑代理和负载均衡器的情况
        """
        # 优先检查代理头
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # X-Forwarded-For可能包含多个IP，取第一个
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()
        
        # 回退到直接连接IP
        return request.client.host if request.client else "unknown"
    
    def _cleanup_expired_records(self):
        """
        清理过期的请求记录
        """
        current_time = time.time()
        
        # 检查是否需要清理
        if current_time - self.last_cleanup < self.cleanup_interval:
            return
        
        cutoff_time = current_time - self.window_size
        cleaned_ips = []
        
        for ip, timestamps in list(self.ip_requests.items()):
            # 过滤掉过期的时间戳
            valid_timestamps = [ts for ts in timestamps if ts > cutoff_time]
            
            if valid_timestamps:
                self.ip_requests[ip] = valid_timestamps
            else:
                # 如果没有有效时间戳，删除这个IP记录
                del self.ip_requests[ip]
                cleaned_ips.append(ip)
        
        self.last_cleanup = current_time
        
        if cleaned_ips:
            logger.debug(f"Cleaned up expired records for {len(cleaned_ips)} IPs")
    
    def _is_rate_limited(self, ip: str) -> Tuple[bool, int, int]:
        """
        检查IP是否超过速率限制
        
        Args:
            ip: 客户端IP地址
            
        Returns:
            Tuple[bool, int, int]: (是否限制, 当前请求数, 剩余请求数)
        """
        current_time = time.time()
        cutoff_time = current_time - self.window_size
        
        # 获取该IP的请求记录
        if ip not in self.ip_requests:
            self.ip_requests[ip] = []
        
        # 过滤掉过期的请求
        valid_requests = [ts for ts in self.ip_requests[ip] if ts > cutoff_time]
        self.ip_requests[ip] = valid_requests
        
        current_requests = len(valid_requests)
        remaining_requests = max(0, self.requests_per_minute - current_requests)
        
        # 检查是否超限
        is_limited = current_requests >= self.requests_per_minute
        
        if not is_limited:
            # 记录当前请求
            self.ip_requests[ip].append(current_time)
            current_requests += 1
            remaining_requests -= 1
        
        return is_limited, current_requests, remaining_requests
    
    def _add_rate_limit_headers(self, response: Response, current_requests: int, remaining_requests: int):
        """
        添加速率限制相关的响应头
        """
        response.headers["X-RateLimit-Limit"] = str(self.requests_per_minute)
        response.headers["X-RateLimit-Remaining"] = str(remaining_requests)
        response.headers["X-RateLimit-Reset"] = str(int(time.time() + self.window_size))
        response.headers["X-RateLimit-Window"] = str(self.window_size)
    
    async def dispatch(self, request: Request, call_next):
        """
        处理请求的中间件逻辑
        """
        # 定期清理过期记录
        self._cleanup_expired_records()
        
        # 获取客户端IP
        client_ip = self._get_client_ip(request)
        
        # 检查速率限制
        is_limited, current_requests, remaining_requests = self._is_rate_limited(client_ip)
        
        if is_limited:
            # 记录限制日志
            logger.warning(
                f"Rate limit exceeded for IP {client_ip}: "
                f"{current_requests}/{self.requests_per_minute} requests in {self.window_size}s"
            )
            
            # 返回429错误
            error_response = JSONResponse(
                status_code=429,
                content={
                    "error": "Rate limit exceeded",
                    "message": f"Too many requests. Limit: {self.requests_per_minute} requests per minute",
                    "retry_after": self.window_size
                }
            )
            
            # 添加速率限制头
            self._add_rate_limit_headers(error_response, current_requests, remaining_requests)
            
            return error_response
        
        # 继续处理请求
        response = await call_next(request)
        
        # 添加速率限制头到正常响应
        self._add_rate_limit_headers(response, current_requests, remaining_requests)
        
        # 记录请求日志（仅在debug模式）
        logger.debug(
            f"Request from {client_ip}: {current_requests}/{self.requests_per_minute}, "
            f"remaining: {remaining_requests}"
        )
        
        return response