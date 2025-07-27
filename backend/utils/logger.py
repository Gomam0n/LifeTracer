import logging
import os
from datetime import datetime
from logging.handlers import RotatingFileHandler
from typing import Optional

def setup_logger(
    name: str = "LifeTracer",
    log_level: str = "INFO",
    log_dir: str = "logs",
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> logging.Logger:
    """设置日志记录器"""
    
    # 确保日志目录存在
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建logger
    logger = logging.getLogger(name)
    
    # 如果logger已经配置过，直接返回
    if logger.handlers:
        return logger
    
    # 设置日志级别
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # 文件处理器 - 所有日志
    log_file = os.path.join(log_dir, f"{name.lower()}.log")
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    
    # 错误日志文件处理器
    error_log_file = os.path.join(log_dir, f"{name.lower()}_error.log")
    error_handler = RotatingFileHandler(
        error_log_file,
        maxBytes=max_file_size,
        backupCount=backup_count,
        encoding='utf-8'
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(formatter)
    logger.addHandler(error_handler)
    
    # 防止日志重复
    logger.propagate = False
    
    return logger

def get_logger(name: Optional[str] = None) -> logging.Logger:
    """获取日志记录器实例"""
    if name is None:
        name = "LifeTracer"
    
    # 如果是模块名，提取最后一部分
    if '.' in name:
        name = name.split('.')[-1]
    
    return setup_logger(name)

class LoggerMixin:
    """日志记录器混入类"""
    
    @property
    def logger(self) -> logging.Logger:
        """获取当前类的日志记录器"""
        if not hasattr(self, '_logger'):
            class_name = self.__class__.__name__
            self._logger = get_logger(class_name)
        return self._logger

def log_function_call(func):
    """函数调用日志装饰器"""
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"调用函数: {func.__name__}")
        
        try:
            result = func(*args, **kwargs)
            logger.debug(f"函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"函数 {func.__name__} 执行失败: {str(e)}")
            raise
    
    return wrapper

async def log_async_function_call(func):
    """异步函数调用日志装饰器"""
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        logger.debug(f"调用异步函数: {func.__name__}")
        
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"异步函数 {func.__name__} 执行成功")
            return result
        except Exception as e:
            logger.error(f"异步函数 {func.__name__} 执行失败: {str(e)}")
            raise
    
    return wrapper

class RequestLogger:
    """请求日志记录器"""
    
    def __init__(self):
        self.logger = get_logger("RequestLogger")
    
    def log_request(self, method: str, url: str, params: dict = None, headers: dict = None):
        """记录请求日志"""
        log_data = {
            "method": method,
            "url": url,
            "timestamp": datetime.now().isoformat()
        }
        
        if params:
            log_data["params"] = params
        
        if headers:
            # 过滤敏感信息
            safe_headers = {k: v for k, v in headers.items() 
                          if k.lower() not in ['authorization', 'x-api-key']}
            log_data["headers"] = safe_headers
        
        self.logger.info(f"API请求: {log_data}")
    
    def log_response(self, status_code: int, response_time: float, error: str = None):
        """记录响应日志"""
        log_data = {
            "status_code": status_code,
            "response_time": f"{response_time:.3f}s",
            "timestamp": datetime.now().isoformat()
        }
        
        if error:
            log_data["error"] = error
            self.logger.error(f"API响应错误: {log_data}")
        else:
            self.logger.info(f"API响应成功: {log_data}")

# 全局请求日志记录器实例
request_logger = RequestLogger()