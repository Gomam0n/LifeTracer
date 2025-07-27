#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
开发环境启动脚本
同时启动前端和后端服务
"""

import os
import sys
import subprocess
import threading
import time
import webbrowser
from pathlib import Path

def start_backend():
    """启动后端服务"""
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    print("🚀 启动后端服务...")
    try:
        # 启动后端服务
        subprocess.run([sys.executable, "start.py", "--host", "0.0.0.0", "--port", "8000", "--dev"], check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 后端服务启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ 后端服务已停止")

def start_frontend():
    """启动前端服务（支持热重载）"""
    frontend_dir = Path(__file__).parent / "frontend"
    
    print("🌐 启动前端服务（热重载模式）...")
    try:
        # 尝试使用livereload库
        try:
            from livereload import Server
            
            server = Server()
            
            # 监控HTML文件变化
            server.watch(str(frontend_dir / '*.html'))
            # 监控CSS文件变化
            server.watch(str(frontend_dir / 'css' / '*.css'))
            # 监控JS文件变化
            server.watch(str(frontend_dir / 'js' / '*.js'))
            
            print("📁 正在监控文件变化:")
            print("   - HTML文件: *.html")
            print("   - CSS文件: css/*.css")
            print("   - JS文件: js/*.js")
            print("💡 修改文件后浏览器将自动刷新")
            
            # 启动服务器
            server.serve(root=str(frontend_dir), port=3000, host='localhost')
            
        except ImportError:
            print("⚠️ livereload库未安装，使用标准HTTP服务器")
            print("💡 要启用热重载功能，请运行: pip install livereload")
            # 回退到标准HTTP服务器
            os.chdir(frontend_dir)
            subprocess.run([sys.executable, "-m", "http.server", "3000"], check=True)
            
    except subprocess.CalledProcessError as e:
        print(f"❌ 前端服务启动失败: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n⏹️ 前端服务已停止")

def open_browser():
    """延迟打开浏览器"""
    time.sleep(3)  # 等待服务启动
    print("🌍 正在打开浏览器...")
    webbrowser.open('http://localhost:3000')

def main():
    """主函数"""
    print("="*50)
    print("🎯 LifeTracer 开发环境启动器")
    print("="*50)
    
    # 检查livereload依赖
    try:
        import livereload
        print("✅ 热重载功能已启用")
    except ImportError:
        print("⚠️ 热重载功能未启用")
        print("💡 要启用热重载，请运行: pip install livereload")
    
    # 检查目录结构
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    frontend_dir = project_root / "frontend"
    
    if not backend_dir.exists():
        print("❌ 后端目录不存在")
        sys.exit(1)
        
    if not frontend_dir.exists():
        print("❌ 前端目录不存在")
        sys.exit(1)
    
    print("📁 项目结构检查通过")
    print("🔧 准备启动服务...")
    print()
    
    try:
        # 在后台线程启动前端服务
        frontend_thread = threading.Thread(target=start_frontend, daemon=True)
        frontend_thread.start()
        
        # 在后台线程打开浏览器
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # 在主线程启动后端服务
        time.sleep(1)  # 稍等一下让前端先启动
        start_backend()
        
    except KeyboardInterrupt:
        print("\n👋 正在停止所有服务...")
        print("✅ 服务已停止")
        sys.exit(0)

if __name__ == "__main__":
    main()