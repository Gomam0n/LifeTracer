# -*- coding: utf-8 -*-
"""
缓存工厂模块
支持动态选择缓存后端：文件缓存 或 Redis缓存
通过配置文件或环境变量控制
"""
import os
from typing import Union
from utils.logger import get_logger

logger = get_logger(__name__)

def create_cache_manager() -> Union['CacheManager', 'RedisCacheManager']:
    """
    缓存管理器工厂函数
    根据配置自动选择合适的缓存后端
    
    优先级：
    1. 环境变量 CACHE_TYPE
    2. 环境变量 REDIS_URL 存在则使用 Redis
    3. 默认使用文件缓存
    
    Returns:
        缓存管理器实例
    """
    cache_type = os.environ.get('CACHE_TYPE', '').lower()
    redis_url = os.environ.get('REDIS_URL', '')
    
    # 显式指定缓存类型
    if cache_type == 'redis':
        return _create_redis_cache(redis_url)
    elif cache_type == 'file':
        return _create_file_cache()
    
    # 自动检测：如果有 Redis URL 则优先使用 Redis
    if redis_url:
        try:
            return _create_redis_cache(redis_url)
        except Exception as e:
            logger.warning(f"Redis 缓存初始化失败，回退到文件缓存: {str(e)}")
            return _create_file_cache()
    
    # 默认使用文件缓存
    return _create_file_cache()

def _create_redis_cache(redis_url: str = None):
    """创建 Redis 缓存管理器"""
    try:
        from caching.redis_cache_manager import RedisCacheManager
        
        if not redis_url:
            redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379')
        
        cache_manager = RedisCacheManager(redis_url=redis_url)
        logger.info(f"使用 Redis 缓存: {redis_url}")
        return cache_manager
        
    except ImportError:
        logger.error("Redis 缓存依赖未安装，请运行: pip install aioredis")
        raise Exception("Redis 缓存依赖未安装")
    except Exception as e:
        logger.error(f"Redis 缓存初始化失败: {str(e)}")
        raise

def _create_file_cache():
    """创建文件缓存管理器"""
    from caching.cache_manager import CacheManager
    
    cache_dir = os.environ.get('CACHE_DIR', 'cache')
    cache_manager = CacheManager(cache_dir=cache_dir)
    logger.info(f"使用文件缓存: {cache_dir}")
    return cache_manager

# 全局缓存管理器实例 (懒加载)
_cache_manager = None

def get_cache_manager():
    """
    获取全局缓存管理器实例
    单例模式，确保整个应用使用同一个缓存实例
    """
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = create_cache_manager()
    return _cache_manager