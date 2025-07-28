#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LifeTracer 一体化生产环境启动脚本
前后端一体化部署，只需启动一个服务
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

def check_dependencies():
    """检查必要的依赖是否已安装"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'aiohttp',
        'aiofiles',
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            missing_packages.append(package)
            print(f"❌ {package}")
    
    if missing_packages:
        print(f"\n⚠️ 缺少以下依赖包: {', '.join(missing_packages)}")
        print("请运行以下命令安装依赖:")
        print("pip install -r requirements.txt")
        return False
    
    print("✅ 所有依赖检查通过")
    return True

def check_frontend_files():
    """检查前端文件是否存在"""
    project_root = Path(__file__).parent
    frontend_dir = project_root / "frontend"
    index_file = frontend_dir / "index.html"
    
    if not frontend_dir.exists():
        print("⚠️ 前端目录不存在")
        return False
    
    if not index_file.exists():
        print("⚠️ 前端index.html文件不存在")
        return False
    
    print("✅ 前端文件检查通过")
    return True

def setup_environment():
    """设置环境变量"""
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    os.environ.setdefault('PYTHONPATH', str(backend_dir))
    
    # 检查必要的环境变量
    required_env_vars = ['OPENAI_API_KEY']
    missing_vars = []
    
    for var in required_env_vars:
        if not os.environ.get(var):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"⚠️ 缺少以下环境变量: {', '.join(missing_vars)}")
        print("请设置这些环境变量或创建 .env 文件")
        return False
    
    return True

def start_server(host="0.0.0.0", port=8000, workers=1, production=False):
    """启动一体化服务器"""
    backend_dir = Path(__file__).parent / "backend"
    
    if not backend_dir.exists():
        print("❌ 后端目录不存在")
        return False
    
    os.chdir(backend_dir)
    
    if production:
        # 生产模式：尝试使用gunicorn
        try:
            import gunicorn
            cmd = [
                "gunicorn",
                "main:app",
                "--worker-class", "uvicorn.workers.UvicornWorker",
                "--workers", str(workers),
                "--bind", f"{host}:{port}",
                "--timeout", "120",
                "--keep-alive", "5",
                "--access-logfile", "-",
                "--error-logfile", "-",
                "--log-level", "info"
            ]
            print("🚀 使用 Gunicorn 启动生产服务器...")
        except ImportError:
            print("⚠️ gunicorn未安装，使用uvicorn启动")
            cmd = [
                "uvicorn",
                "main:app",
                "--host", host,
                "--port", str(port),
                "--workers", str(workers),
                "--access-log",
                "--log-level", "info"
            ]
    else:
        # 开发模式：使用uvicorn
        cmd = [
            "uvicorn",
            "main:app",
            "--host", host,
            "--port", str(port),
            "--reload",
            "--access-log",
            "--log-level", "info"
        ]
        print("🚀 使用 Uvicorn 启动开发服务器...")
    
    print(f"📍 服务地址: http://{host}:{port}")
    print(f"📚 API文档: http://{host}:{port}/docs")
    print(f"🌐 前端页面: http://{host}:{port}")
    print("="*50)
    
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as e:
        print(f"❌ 服务器启动失败: {e}")
        return False
    except KeyboardInterrupt:
        print("\n⏹️ 服务器已停止")
        return True
    
    return True

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="LifeTracer 一体化启动器")
    
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="服务器监听地址 (默认: 0.0.0.0)"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口 (默认: 8000)"
    )
    
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="工作进程数 (默认: 1)"
    )
    
    parser.add_argument(
        "--prod",
        action="store_true",
        help="生产模式启动"
    )
    
    parser.add_argument(
        "--check-deps",
        action="store_true",
        help="只检查依赖，不启动服务器"
    )
    
    parser.add_argument(
        "--no-check",
        action="store_true",
        help="跳过依赖检查"
    )
    
    return parser.parse_args()

def main():
    """主函数"""
    print("="*60)
    print("🎯 LifeTracer 一体化启动器")
    print("📝 前后端一体化部署，只需启动一个服务")
    print("="*60)
    
    args = parse_args()
    
    # 检查依赖
    if not args.no_check:
        print("🔍 检查依赖...")
        if not check_dependencies():
            sys.exit(1)
        print()
        
        print("🔍 检查前端文件...")
        if not check_frontend_files():
            print("⚠️ 前端文件检查失败，但将继续启动...")
        print()
    
    # 如果只是检查依赖，则退出
    if args.check_deps:
        print("✅ 检查完成")
        sys.exit(0)
    
    # 设置环境
    print("🔧 设置环境...")
    if not setup_environment():
        print("⚠️ 环境设置有问题，但将继续启动...")
    print()
    
    # 启动服务器
    success = start_server(args.host, args.port, args.workers, args.prod)
    
    if not success:
        print("❌ 服务器启动失败")
        sys.exit(1)

if __name__ == "__main__":
    main()