# -*- coding: utf-8 -*-
"""
Redis 缓存管理器
"""
import json
import asyncio
from typing import Any, Optional
import redis.asyncio as redis
from utils.logger import get_logger

logger = get_logger(__name__)

class RedisCacheManager:
    """
    Redis 缓存管理器
    """
    
    def __init__(self, redis_url: str = "redis://localhost:6379", db: int = 0, key_prefix: str = "lifetracer:"):
        """
        初始化 Redis 缓存管理器
        
        Args:
            redis_url: Redis 连接 URL
            db: Redis 数据库编号 (0-15)
            key_prefix: 缓存键前缀，避免与其他应用冲突
        """
        self.redis_url = redis_url
        self.db = db
        self.key_prefix = key_prefix
        self.redis = None
        self._connection_lock = asyncio.Lock()
    
    async def _get_redis(self) -> redis.Redis:
        """
        获取 Redis 连接 (懒加载 + 连接池)
        使用连接池提高并发性能
        """
        if self.redis is None:
            async with self._connection_lock:
                if self.redis is None:  # 双重检查锁定
                    try:
                        self.redis = redis.from_url(
                            self.redis_url,
                            db=self.db,
                            encoding="utf-8",
                            decode_responses=True,
                            max_connections=20,  # 连接池大小
                            retry_on_timeout=True
                        )
                        # 测试连接
                        await self.redis.ping()
                        logger.info(f"Redis 连接成功: {self.redis_url}")
                    except Exception as e:
                        logger.error(f"Redis 连接失败: {str(e)}")
                        raise Exception(f"无法连接到 Redis: {str(e)}")
        return self.redis
    
    def _get_cache_key(self, key: str) -> str:
        """
        生成完整的缓存键
        添加前缀避免键冲突
        """
        return f"{self.key_prefix}{key}"
    
    async def get(self, key: str) -> Optional[Any]:
        """
        获取缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            缓存的数据，如果不存在或已过期返回 None
        """
        try:
            redis = await self._get_redis()
            cache_key = self._get_cache_key(key)
            
            # Redis 会自动处理过期，如果键过期会返回 None
            cached_data = await redis.get(cache_key)
            
            if cached_data is None:
                logger.debug(f"缓存未命中: {key}")
                return None
            
            # 反序列化数据
            try:
                data = json.loads(cached_data)
                logger.debug(f"缓存命中: {key}")
                return data
            except json.JSONDecodeError as e:
                logger.warning(f"缓存数据格式错误 {key}: {str(e)}")
                # 删除损坏的缓存
                await redis.delete(cache_key)
                return None
                
        except Exception as e:
            logger.error(f"读取缓存失败 {key}: {str(e)}")
            return None
    
    async def set(self, key: str, data: Any, expire: Optional[int] = None) -> bool:
        """
        设置缓存数据
        
        Args:
            key: 缓存键
            data: 要缓存的数据
            expire: 过期时间（秒），None 表示永不过期
            
        Returns:
            设置成功返回 True，失败返回 False
        """
        try:
            redis = await self._get_redis()
            cache_key = self._get_cache_key(key)
            
            # 序列化数据
            try:
                serialized_data = json.dumps(data, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                logger.error(f"数据序列化失败 {key}: {str(e)}")
                return False
            
            # 设置缓存，Redis 原生支持过期时间
            if expire:
                await redis.setex(cache_key, expire, serialized_data)
                logger.debug(f"缓存设置 (过期时间: {expire}s): {key}")
            else:
                await redis.set(cache_key, serialized_data)
                logger.debug(f"缓存设置 (永久): {key}")
            
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        删除缓存数据
        
        Args:
            key: 缓存键
            
        Returns:
            删除成功返回 True，失败返回 False
        """
        try:
            redis = await self._get_redis()
            cache_key = self._get_cache_key(key)
            
            deleted_count = await redis.delete(cache_key)
            success = deleted_count > 0
            
            if success:
                logger.debug(f"缓存删除成功: {key}")
            else:
                logger.debug(f"缓存不存在: {key}")
                
            return success
            
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {str(e)}")
            return False
    
    async def clear_expired(self) -> int:
        """
        清理过期的缓存
        
        注意：Redis 会自动清理过期键，此方法主要用于兼容原接口
        实际上不需要手动清理
        
        Returns:
            清理的缓存数量 (Redis 自动清理，返回 0)
        """
        logger.info("Redis 自动处理过期键，无需手动清理")
        return 0
    
    async def get_cache_stats(self) -> dict:
        """
        获取缓存统计信息
        
        Returns:
            包含缓存统计信息的字典
        """
        try:
            redis = await self._get_redis()
            
            # 获取所有匹配前缀的键
            pattern = f"{self.key_prefix}*"
            keys = await redis.keys(pattern)
            
            stats = {
                'total_keys': len(keys),
                'total_memory': 0,
                'expired_keys': 0,  # Redis 自动清理，无法统计
                'valid_keys': len(keys),
                'redis_info': {}
            }
            
            # 获取内存使用情况
            if keys:
                # 计算所有键的内存使用 (近似值)
                memory_usage = 0
                for key in keys[:100]:  # 限制检查数量，避免性能问题
                    try:
                        size = await redis.memory_usage(key)
                        if size:
                            memory_usage += size
                    except:
                        pass  # 某些 Redis 版本可能不支持 MEMORY USAGE
                
                # 估算总内存使用
                if len(keys) > 100:
                    stats['total_memory'] = int(memory_usage * len(keys) / 100)
                else:
                    stats['total_memory'] = memory_usage
            
            # 获取 Redis 服务器信息
            try:
                info = await redis.info()
                stats['redis_info'] = {
                    'redis_version': info.get('redis_version', 'unknown'),
                    'used_memory': info.get('used_memory', 0),
                    'used_memory_human': info.get('used_memory_human', '0B'),
                    'connected_clients': info.get('connected_clients', 0),
                    'total_commands_processed': info.get('total_commands_processed', 0)
                }
            except:
                pass
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return {
                'total_keys': 0,
                'total_memory': 0,
                'expired_keys': 0,
                'valid_keys': 0,
                'redis_info': {}
            }
    
    async def close(self):
        """
        关闭 Redis 连接
        在应用关闭时调用
        """
        if self.redis:
            try:
                await self.redis.close()
                logger.info("Redis 连接已关闭")
            except Exception as e:
                logger.error(f"关闭 Redis 连接失败: {str(e)}")
    
    async def ping(self) -> bool:
        """
        测试 Redis 连接
        
        Returns:
            连接正常返回 True，否则返回 False
        """
        try:
            redis = await self._get_redis()
            await redis.ping()
            return True
        except Exception as e:
            logger.error(f"Redis 连接测试失败: {str(e)}")
            return False


# 为了保持向后兼容，提供一个别名
CacheManager = RedisCacheManager