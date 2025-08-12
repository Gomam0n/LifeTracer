class Config:
    """配置管理类"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = config_file
        self.config_data = {}
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        
# 全局配置实例
_config_instance = None

def get_config() -> Config:
    """获取全局配置实例"""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config()
    return _config_instance

def init_config(config_file: str = "config.json") -> Config:
    """初始化配置"""
    global _config_instance
    _config_instance = Config(config_file)
    return _config_instance