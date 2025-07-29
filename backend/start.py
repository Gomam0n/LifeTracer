#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LifeTracer Backend 启动脚本

使用方法:
    python start.py                    # 开发模式启动
    python start.py --prod             # 生产模式启动
    python start.py --host 0.0.0.0     # 指定主机
    python start.py --port 8080        # 指定端口
    python start.py --workers 4        # 指定工作进程数（生产模式）
"""

import argparse
import os
import sys
import uvicorn
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from utils.logger import get_logger
logger = get_logger(__name__)

def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description='LifeTracer Backend Server')
    
    parser.add_argument(
        '--host',
        type=str,
        default=None,
        help='服务器主机地址 (默认从配置文件读取)'
    )
    
    parser.add_argument(
        '--port',
        type=int,
        default=None,
        help='服务器端口 (默认从配置文件读取)'
    )
    
    parser.add_argument(
        '--prod',
        action='store_true',
        help='生产模式启动'
    )
    
    parser.add_argument(
        '--dev',
        action='store_true',
        help='开发模式启动（默认）'
    )
    
    parser.add_argument(
        '--workers',
        type=int,
        default=1,
        help='工作进程数（仅生产模式）'
    )
    
    parser.add_argument(
        '--reload',
        action='store_true',
        help='启用自动重载（开发模式）'
    )
    
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['debug', 'info', 'warning', 'error'],
        default='info',
        help='日志级别'
    )
    
    parser.add_argument(
        '--config',
        type=str,
        default='config.json',
        help='配置文件路径'
    )
    
    return parser.parse_args()

def check_dependencies():
    """检查依赖是否安装"""
    required_packages = [
        'fastapi',
        'uvicorn',
        'pydantic',
        'aiohttp',
        'aiofiles'
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    if missing_packages:
        logger.error(f"❌ 缺少以下依赖包: {', '.join(missing_packages)}")
        logger.error("请运行: pip install -r requirements.txt")
        sys.exit(1)
    
    logger.info("✅ 所有依赖包已安装")

def check_config(config_file):
    """检查配置文件"""
    if not os.path.exists(config_file):
        logger.warning("⚠️  配置文件不存在，将使用默认配置")
    else:
        logger.info(f"✅ 使用配置文件: {config_file}")

def setup_environment():
    """设置环境"""
    # 创建必要的目录
    directories = ['logs', 'cache']
    
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logger.info(f"📁 创建目录: {directory}")

def print_startup_info(config, host, port, is_prod):
    """打印启动信息"""
    mode = "生产模式" if is_prod else "开发模式"
    
    logger.info("\n" + "="*50)
    logger.info(f"🚀 LifeTracer Backend 启动中...")
    logger.info(f"📋 模式: {mode}")
    logger.info(f"🌐 地址: http://{host}:{port}")
    logger.info(f"📚 API文档: http://{host}:{port}/docs")
    logger.info(f"🔧 配置: {config.config_file}")
    
    logger.info("="*50 + "\n")

def main():
    """主函数"""
    args = parse_args()
    
    # 检查依赖
    check_dependencies()
    
    # 检查配置
    check_config(args.config)
    
    # 设置环境
    setup_environment()
    
    # 初始化配置
    from utils.config import init_config
    config = init_config(args.config)
    
    # 确定运行参数
    host = args.host 
    port = args.port 
    is_prod = args.prod or (not args.dev)
    
    # 打印启动信息
    print_startup_info(config, host, port, is_prod)
    
    # 启动服务器
    if is_prod:
        # 生产模式
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            workers=args.workers,
            log_level=args.log_level,
            access_log=True
        )
    else:
        # 开发模式
        uvicorn.run(
            "main:app",
            host=host,
            port=port,
            reload=args.reload or True,
            log_level=args.log_level,
            access_log=True
        )

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 启动失败: {e}")
        sys.exit(1)