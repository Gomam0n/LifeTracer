# -*- coding: utf-8 -*-
"""
Validation Middleware for LifeTracer
人物姓名验证中间件
"""

import re
from typing import Optional, Tuple
from fastapi import Request
from fastapi.responses import JSONResponse
from utils.logger import get_logger

logger = get_logger(__name__)


class InputValidator:
    """
    验证器
    
    主要功能：
    - 人物姓名验证：支持中英文姓名格式
    - 长度限制：防止过长输入
    - 特殊字符过滤：防止注入攻击
    - 格式规范化：统一输入格式
    """
    
    # 中文姓名模式：支持汉字、·（间隔号）
    CHINESE_NAME_PATTERN = re.compile(r'^[\u4e00-\u9fff·]{1,20}$')
    
    # 英文姓名模式：支持字母、空格、连字符、撇号、点号
    ENGLISH_NAME_PATTERN = re.compile(r'^[a-zA-Z\s\-\'\.À-\u017F]{1,50}$')
    
    # 混合姓名模式：中英文混合（如：李小明 John）
    MIXED_NAME_PATTERN = re.compile(r'^[\u4e00-\u9fff·a-zA-Z\s\-\'\.À-\u017F]{1,50}$')
    
    # 危险字符模式：SQL注入、XSS等攻击字符
    DANGEROUS_PATTERNS = [
        re.compile(r'[<>"\'\/\\]'),  # HTML/XML标签字符
        re.compile(r'(script|javascript|vbscript)', re.IGNORECASE),  # 脚本关键词
        re.compile(r'(select|insert|update|delete|drop|union)', re.IGNORECASE),  # SQL关键词
        re.compile(r'[\x00-\x1f\x7f-\x9f]'),  # 控制字符
        re.compile(r'(\-\-|\/\*|\*\/|;)'),  # SQL注释字符
    ]
    
    @classmethod
    def validate_person_name(cls, name: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        验证人物姓名
        
        Args:
            name: 待验证的姓名
            
        Returns:
            Tuple[bool, Optional[str], Optional[str]]: 
            (是否有效, 清理后的姓名, 错误信息)
        """
        if not name:
            return False, None, "姓名不能为空"
        
        # 去除首尾空格
        cleaned_name = name.strip()
        
        if not cleaned_name:
            return False, None, "姓名不能为空"
        
        # 长度检查
        if len(cleaned_name) > 50:
            return False, None, "姓名长度不能超过50个字符"
        
        if len(cleaned_name) < 1:
            return False, None, "姓名长度不能少于1个字符"
        
        # 危险字符检查
        for pattern in cls.DANGEROUS_PATTERNS:
            if pattern.search(cleaned_name):
                logger.warning(f"Detected dangerous characters in name: {name}")
                return False, None, "姓名包含不允许的字符"
        
        # 格式验证
        is_valid_format = (
            cls.CHINESE_NAME_PATTERN.match(cleaned_name) or
            cls.ENGLISH_NAME_PATTERN.match(cleaned_name) or
            cls.MIXED_NAME_PATTERN.match(cleaned_name)
        )
        
        if not is_valid_format:
            return False, None, "姓名格式不正确，请输入有效的中文或英文姓名"
        
        # 进一步清理：规范化空格
        normalized_name = re.sub(r'\s+', ' ', cleaned_name)
        
        # 检查是否为纯空格或特殊字符
        if not re.search(r'[\u4e00-\u9fffa-zA-Z]', normalized_name):
            return False, None, "姓名必须包含有效的中文或英文字符"
        
        logger.debug(f"Name validation passed: {normalized_name}")
        return True, normalized_name, None


async def validate_person_name_middleware(request: Request, call_next):
    """
    人物姓名验证中间件
    
    对 /api/biography 接口的请求进行人物姓名验证
    """
    # 只对 /api/biography 接口进行验证
    if request.url.path == "/api/biography" and request.method == "POST":
        try:
            # 获取请求体
            body = await request.body()
            if body:
                import json
                try:
                    request_data = json.loads(body)
                    name = request_data.get("name")
                    
                    if name:
                        # 验证人物姓名
                        is_valid, cleaned_name, error_msg = InputValidator.validate_person_name(name)
                        if not is_valid:
                            logger.error(f"Name validation failed: {error_msg}")
                            return JSONResponse(
                                status_code=400,
                                content={
                                    "error": "输入验证失败",
                                    "message": error_msg,
                                    "field": "name"
                                }
                            )
                        
                        # 更新请求数据中的姓名为清理后的版本
                        request_data["name"] = cleaned_name
                        
                        # 重新构造请求体
                        new_body = json.dumps(request_data).encode()
                        
                        # 创建新的请求对象
                        async def receive():
                            return {"type": "http.request", "body": new_body}
                        
                        request._receive = receive
                        
                except json.JSONDecodeError:
                    pass  # 如果不是JSON格式，让后续处理
                    
        except Exception as e:
            logger.error(f"Validation middleware error: {str(e)}")
            # 中间件出错时抛出验证异常，不继续处理请求
            return JSONResponse(
                status_code=500,
                content={
                    "error": "验证中间件错误",
                    "message": "请求验证过程中发生内部错误",
                    "field": "validation"
                }
            )
    
    response = await call_next(request)
    return response