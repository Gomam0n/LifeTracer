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

def start_integrated_server():
    """启动一体化服务器（前后端一体）"""
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("🚀 启动一体化服务器（前后端一体）...")
    try:
        # 启动一体化服务器
        subprocess.run([sys.executable, "start.py", "--host", "127.0.0.1", "--port", "8000", "--dev"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ 服务器已停止")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(3)  # 等待服务启动
    print("🌍 正在打开浏览器...")
    webbrowser.open('http://localhost:8000')  # 改为8000端口

def check_file_structure():
    """检查文件结构"""
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"
    
    if not backend_dir.exists():
        print("❌ 后端目录不存在")
        return False
        
    if not frontend_dir.exists():
        print("❌ 前端目录不存在")
        return False
    
    # 检查关键文件
    main_py = backend_dir / "main.py"
    index_html = frontend_dir / "index.html"
    
    if not main_py.exists():
        print("❌ backend/main.py 不存在")
        return False
        
    if not index_html.exists():
        print("❌ frontend/index.html 不存在")
        return False
    
    print("✅ 项目结构检查通过")
    return True

def main():
    """主函数"""
    print("="*60)
    print("🎯 LifeTracer 开发环境启动器")
    print("📝 一体化部署：前后端通过同一服务器提供")
    print("="*60)
    
    # 检查文件结构
    if not check_file_structure():
        sys.exit(1)
    
    print("🔧 准备启动一体化服务器...")
    print("📍 服务地址: http://localhost:8000")
    print("📚 API文档: http://localhost:8000/docs")
    print("🌐 前端页面: http://localhost:8000")
    print()
    
    try:
        # 在后台线程打开浏览器
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # 在主线程启动一体化服务器
        start_integrated_server()
        
    except KeyboardInterrupt:
        print("\n👋 正在停止服务...")
        print("✅ 服务已停止")
        sys.exit(0)

if __name__ == "__main__":
    main()