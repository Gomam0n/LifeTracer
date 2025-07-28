#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LifeTracer Render部署启动脚本
专门为Render Web Service优化的启动配置
"""

import os
import sys
from pathlib import Path

def setup_environment():
    """设置Render部署环境"""
    # 添加backend目录到Python路径
    project_root = Path(__file__).parent
    backend_dir = project_root / "backend"
    
    if str(backend_dir) not in sys.path:
        sys.path.insert(0, str(backend_dir))
    
    os.environ.setdefault('PYTHONPATH', str(backend_dir))
    
    # Render会自动设置PORT环境变量
    port = os.environ.get('PORT', '8000')
    host = '0.0.0.0'  # Render要求绑定到0.0.0.0
    
    print(f"🌐 Render部署配置:")
    print(f"   Host: {host}")
    print(f"   Port: {port}")
    print(f"   Backend目录: {backend_dir}")
    
    return host, int(port)

def main():
    """Render启动入口"""
    print("🚀 LifeTracer Render部署启动中...")
    
    # 设置环境
    host, port = setup_environment()
    
    # 切换到backend目录
    backend_dir = Path(__file__).parent / "backend"
    os.chdir(backend_dir)
    
    # 导入并启动FastAPI应用
    try:
        import uvicorn
        from main import app
        
        print("✅ 成功导入应用")
        print(f"📍 启动服务: http://{host}:{port}")
        
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
        print(f"❌ 启动失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()