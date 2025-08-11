#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LifeTracer Render部署启动脚本
专门为Render Web Service优化的启动配置
"""

import os
import sys
import subprocess
import time
from pathlib import Path

# 添加backend目录到Python路径以导入logger
backend_dir = Path(__file__).parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.logger import get_logger
logger = get_logger(__name__)

def check_redis_running():
    """检查Redis是否正在运行"""
    try:
        # 尝试连接Redis
        result = subprocess.run(['redis-cli', 'ping'], 
                              capture_output=True, text=True, timeout=5)
        return result.returncode == 0 and 'PONG' in result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False

def start_redis_server():
    """启动Redis服务器（生产环境）"""
    if check_redis_running():
        logger.info("✅ Redis服务已在运行")
        return True
    
    # 在生产环境中，通常Redis应该作为系统服务运行
    # 这里只做基本的启动尝试
    logger.info("🔄 正在尝试启动Redis服务...")
    
    try:
        # 尝试启动Redis服务
        if os.name == 'nt':
            # Windows系统
            try:
                subprocess.run(['net', 'start', 'Redis'], 
                             capture_output=True, check=True)
                logger.info("✅ Redis Windows服务启动成功")
                return True
            except subprocess.CalledProcessError:
                logger.warning("⚠️ Redis Windows服务启动失败")
        else:
            # Linux系统 - 尝试systemctl启动
            try:
                subprocess.run(['systemctl', 'start', 'redis'], 
                             capture_output=True, check=True)
                time.sleep(2)
                if check_redis_running():
                    logger.info("✅ Redis systemd服务启动成功")
                    return True
            except (subprocess.CalledProcessError, FileNotFoundError):
                # 如果systemctl不可用，尝试直接启动
                try:
                    subprocess.Popen(['redis-server'], 
                                   stdout=subprocess.DEVNULL, 
                                   stderr=subprocess.DEVNULL)
                    time.sleep(2)
                    if check_redis_running():
                        logger.info("✅ Redis服务器启动成功")
                        return True
                except FileNotFoundError:
                    logger.warning("⚠️ 未找到Redis，请确保已安装Redis")
        
        logger.warning("⚠️ Redis启动失败，将使用文件缓存")
        return False
        
    except Exception as e:
        logger.warning(f"⚠️ Redis启动异常: {e}，将使用文件缓存")
        return False

def setup_environment():
    """设置Render部署环境"""
    # 添加backend目录到Python路径
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    os.environ.setdefault('PYTHONPATH', str(backend_dir))
    
    # 启动Redis服务
    redis_started = start_redis_server()
    
    # 设置Redis缓存环境变量
    if redis_started:
        os.environ.setdefault('CACHE_TYPE', 'redis')
        # 生产环境Redis URL，如果没有设置则使用默认值
        os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
        logger.info(f"🔧 已启用Redis缓存: {os.environ.get('REDIS_URL')}")
    else:
        os.environ.setdefault('CACHE_TYPE', 'file')
        logger.info("🔧 Redis不可用，使用文件缓存")
    
    # Render会自动设置PORT环境变量
    port = os.environ.get('PORT', '8000')
    host = '0.0.0.0'  # Render要求绑定到0.0.0.0
    
    logger.info(f"🌐 Render部署配置:")
    logger.info(f"   Host: {host}")
    logger.info(f"   Port: {port}")
    logger.info(f"   Backend目录: {backend_dir}")
    
    return host, int(port)

def main():
    """Render启动入口"""
    logger.info("🚀 LifeTracer Render部署启动中...")
    
    # 设置环境
    host, port = setup_environment()
    
    # 切换到backend目录
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # 导入并启动FastAPI应用
    try:
        import uvicorn
        from main import app
        
        logger.info("✅ 成功导入应用")
        logger.info(f"📍 启动服务: http://{host}:{port}")
        
        # 使用uvicorn启动，适合Render的配置
        uvicorn.run(
            app,
            host=host,
            port=port,
            workers=1,  # Render推荐单worker
            access_log=True,
            log_level="info"
        )
        
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()