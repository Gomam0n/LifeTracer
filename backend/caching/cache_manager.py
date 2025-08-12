import json
import asyncio
from typing import Any, Optional
from datetime import datetime, timedelta
import aiofiles
import os
import hashlib
from utils.logger import get_logger

logger = get_logger(__name__)

class CacheManager:
    def __init__(self, cache_dir: str = "cache"):
        self.cache_dir = cache_dir
        self.ensure_cache_dir()
    
    def ensure_cache_dir(self):
        """确保缓存目录存在"""
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def _get_cache_path(self, key: str) -> str:
        """获取缓存文件路径"""
        # 使用MD5哈希作为文件名，避免特殊字符问题
        key_hash = hashlib.md5(key.encode('utf-8')).hexdigest()
        return os.path.join(self.cache_dir, f"{key_hash}.json")
    
    async def get(self, key: str) -> Optional[Any]:
        """获取缓存数据"""
        try:
            cache_path = self._get_cache_path(key)
            
            if not os.path.exists(cache_path):
                return None
            
            async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                content = await f.read()
                cache_data = json.loads(content)
            
            # 检查是否过期
            expire_time = cache_data.get('expire_time')
            if expire_time:
                expire_datetime = datetime.fromisoformat(expire_time)
                if datetime.now() > expire_datetime:
                    # 缓存已过期，删除文件
                    await self._delete_cache_file(cache_path)
                    return None
            
            logger.debug(f"缓存命中: {key}")
            return cache_data.get('data')
            
        except Exception as e:
            logger.error(f"读取缓存失败 {key}: {str(e)}")
            return None
    
    async def set(self, key: str, data: Any, expire: Optional[int] = None) -> bool:
        """设置缓存数据"""
        try:
            cache_path = self._get_cache_path(key)
            
            cache_data = {
                'data': data,
                'created_time': datetime.now().isoformat(),
                'expire_time': None
            }
            
            if expire:
                expire_time = datetime.now() + timedelta(seconds=expire)
                cache_data['expire_time'] = expire_time.isoformat()
            
            async with aiofiles.open(cache_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(cache_data, ensure_ascii=False, indent=2))
            
            logger.debug(f"缓存设置: {key}")
            return True
            
        except Exception as e:
            logger.error(f"设置缓存失败 {key}: {str(e)}")
            return False
    
    async def delete(self, key: str) -> bool:
        """删除缓存数据"""
        try:
            cache_path = self._get_cache_path(key)
            return await self._delete_cache_file(cache_path)
        except Exception as e:
            logger.error(f"删除缓存失败 {key}: {str(e)}")
            return False
    
    async def _delete_cache_file(self, cache_path: str) -> bool:
        """删除缓存文件"""
        try:
            if os.path.exists(cache_path):
                os.remove(cache_path)
                return True
            return False
        except Exception as e:
            logger.error(f"删除缓存文件失败 {cache_path}: {str(e)}")
            return False
    
    async def clear_expired(self) -> int:
        """清理过期的缓存文件"""
        cleared_count = 0
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    cache_path = os.path.join(self.cache_dir, filename)
                    
                    try:
                        async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                            cache_data = json.loads(content)
                        
                        expire_time = cache_data.get('expire_time')
                        if expire_time:
                            expire_datetime = datetime.fromisoformat(expire_time)
                            if datetime.now() > expire_datetime:
                                await self._delete_cache_file(cache_path)
                                cleared_count += 1
                    
                    except Exception as e:
                        logger.warning(f"检查缓存文件失败 {cache_path}: {str(e)}")
                        # 如果文件损坏，也删除它
                        await self._delete_cache_file(cache_path)
                        cleared_count += 1
            
            logger.info(f"清理了 {cleared_count} 个过期缓存文件")
            return cleared_count
            
        except Exception as e:
            logger.error(f"清理过期缓存失败: {str(e)}")
            return 0
    
    async def get_cache_stats(self) -> dict:
        """获取缓存统计信息"""
        stats = {
            'total_files': 0,
            'total_size': 0,
            'expired_files': 0,
            'valid_files': 0
        }
        
        try:
            for filename in os.listdir(self.cache_dir):
                if filename.endswith('.json'):
                    cache_path = os.path.join(self.cache_dir, filename)
                    stats['total_files'] += 1
                    stats['total_size'] += os.path.getsize(cache_path)
                    
                    try:
                        async with aiofiles.open(cache_path, 'r', encoding='utf-8') as f:
                            content = await f.read()
                            cache_data = json.loads(content)
                        
                        expire_time = cache_data.get('expire_time')
                        if expire_time:
                            expire_datetime = datetime.fromisoformat(expire_time)
                            if datetime.now() > expire_datetime:
                                stats['expired_files'] += 1
                            else:
                                stats['valid_files'] += 1
                        else:
                            stats['valid_files'] += 1
                    
                    except Exception:
                        stats['expired_files'] += 1
            
            return stats
            
        except Exception as e:
            logger.error(f"获取缓存统计失败: {str(e)}")
            return stats