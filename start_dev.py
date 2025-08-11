#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发环境启动脚本
一体化部署：只启动后端服务，前端通过后端提供
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

# 添加backend目录到Python路径以导入logger
backend_dir = Path(__file__).parent / "backend"
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

from utils.logger import get_logger
logger = get_logger(__name__)

def start_integrated_server():
    """启动一体化服务器（前后端一体）"""
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    logger.info("🚀 启动一体化服务器（前后端一体）...")
    try:
        # 启动一体化服务器
        subprocess.run([sys.executable, "start.py", "--host", "127.0.0.1", "--port", "8000", "--dev"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        logger.info("\n⏹️ 服务器已停止")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(3)  # 等待服务启动
    logger.info("🌍 正在打开浏览器...")
    webbrowser.open('http://localhost:8000')  # 改为8000端口

def check_file_structure():
    """检查文件结构"""
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"
    
    if not backend_dir.exists():
        logger.error("❌ 后端目录不存在")
        return False
        
    if not frontend_dir.exists():
        logger.error("❌ 前端目录不存在")
        return False
    
    # 检查关键文件
    main_py = backend_dir / "main.py"
    index_html = frontend_dir / "index.html"
    
    if not main_py.exists():
        logger.error("❌ backend/main.py 不存在")
        return False
        
    if not index_html.exists():
        logger.error("❌ frontend/index.html 不存在")
        return False
    
    logger.info("✅ 项目结构检查通过")
    return True

def main():
    """主函数"""
    logger.info("="*60)
    logger.info("🎯 LifeTracer 开发环境启动器")
    logger.info("📝 一体化部署：前后端通过同一服务器提供")
    logger.info("="*60)
    
    # 设置Redis缓存环境变量（开发环境默认启用）
    os.environ.setdefault('CACHE_TYPE', 'redis')
    os.environ.setdefault('REDIS_URL', 'redis://localhost:6379')
    logger.info("🔧 开发环境默认启用Redis缓存: redis://localhost:6379")
    
    # 检查文件结构
    if not check_file_structure():
        sys.exit(1)
    
    logger.info("🔧 准备启动一体化服务器...")
    logger.info("📍 服务地址: http://localhost:8000")
    logger.info("📚 API文档: http://localhost:8000/docs")
    logger.info("🌐 前端页面: http://localhost:8000")
    logger.info("")
    
    try:
        # 在后台线程打开浏览器
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # 在主线程启动一体化服务器
        start_integrated_server()
        
    except KeyboardInterrupt:
        logger.info("\n👋 正在停止服务...")
        logger.info("✅ 服务已停止")
        sys.exit(0)

if __name__ == "__main__":
    main()