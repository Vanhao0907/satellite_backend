"""
全局配置文件
从环境变量中读取配置，提供默认值
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载.env文件
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

class Config:
    """基础配置类"""
    
    # 环境标识
    ENV = os.getenv('FLASK_ENV', 'development')

    # Flask配置
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'

    # 服务器配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))

    # ========== 新增：服务器URL配置 ==========
    # 用于生成静态文件的访问URL
    SERVER_URL = os.getenv('SERVER_URL', f'http://172.16.1.84:{PORT}')
    #SERVER_URL = os.getenv('SERVER_URL', f'https://bodingly-superurgent-zayn.ngrok-free.dev:{PORT}')

    # 目录配置
    RAW_DATA_DIR = os.path.join(BASE_DIR, os.getenv('RAW_DATA_DIR', 'data/raw'))
    TEMP_DATA_DIR = os.path.join(BASE_DIR, os.getenv('TEMP_DATA_DIR', 'data/temp'))
    LOG_DIR = os.path.join(BASE_DIR, os.getenv('LOG_DIR', 'logs'))

    # ========== 新增：静态文件目录配置 ==========
    STATIC_FILES_DIR = os.path.join(BASE_DIR, os.getenv('STATIC_FILES_DIR', 'data/static'))
    # 静态文件URL前缀（相对于SERVER_URL）
    STATIC_URL_PREFIX = '/static'

    # ========== 系统约束配置 ==========
    MAX_ANTENNAS_PER_STATION = int(os.getenv('MAX_ANTENNAS_PER_STATION', 20))

    # 临时文件清理策略
    AUTO_CLEANUP = os.getenv('AUTO_CLEANUP', 'False').lower() == 'true'
    CLEANUP_KEEP_DAYS = int(os.getenv('CLEANUP_KEEP_DAYS', 7))

    # ========== 新增：静态文件清理策略 ==========
    AUTO_CLEANUP_STATIC = os.getenv('AUTO_CLEANUP_STATIC', 'True').lower() == 'true'
    STATIC_KEEP_DAYS = int(os.getenv('STATIC_KEEP_DAYS', 30))  # 静态文件保留30天

    # 日志配置
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))  # 10MB
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))

    # 算法默认参数
    DEFAULT_STRATEGY = os.getenv('DEFAULT_STRATEGY', 'method_3')
    DEFAULT_TIME_WINDOW = int(os.getenv('DEFAULT_TIME_WINDOW', 300))
    DEFAULT_OPTIMIZATION = os.getenv('DEFAULT_OPTIMIZATION', 'True').lower() == 'true'
    DEFAULT_USE_SA = os.getenv('DEFAULT_USE_SA', 'True').lower() == 'true'
    DEFAULT_SA_MAX_TIME = int(os.getenv('DEFAULT_SA_MAX_TIME', 300))

    # 超时配置
    REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', 300))

    # CORS配置
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', '*')

    # ========== 新增：图片导出配置 ==========
    IMAGE_WIDTH = int(os.getenv('IMAGE_WIDTH', 1280))  # 图片宽度
    IMAGE_HEIGHT = int(os.getenv('IMAGE_HEIGHT', 720))  # 图片高度
    IMAGE_FORMAT = os.getenv('IMAGE_FORMAT', 'jpeg')  # 图片格式：jpeg, png
    IMAGE_QUALITY = int(os.getenv('IMAGE_QUALITY', 60))  # JPG质量：1-100

    # 可选：OSS配置
    OSS_ENABLED = os.getenv('OSS_ENABLED', 'False').lower() == 'true'
    OSS_ENDPOINT = os.getenv('OSS_ENDPOINT', '')
    OSS_ACCESS_KEY_ID = os.getenv('OSS_ACCESS_KEY_ID', '')
    OSS_ACCESS_KEY_SECRET = os.getenv('OSS_ACCESS_KEY_SECRET', '')
    OSS_BUCKET_NAME = os.getenv('OSS_BUCKET_NAME', '')

    @classmethod
    def ensure_directories(cls):
        """确保必要的目录存在"""
        os.makedirs(cls.RAW_DATA_DIR, exist_ok=True)
        os.makedirs(cls.TEMP_DATA_DIR, exist_ok=True)
        os.makedirs(cls.LOG_DIR, exist_ok=True)
        os.makedirs(cls.STATIC_FILES_DIR, exist_ok=True)  # ← 新增

    @classmethod
    def validate(cls):
        """验证配置"""
        # 检查原始数据目录是否存在
        if not os.path.exists(cls.RAW_DATA_DIR):
            print(f"警告: 原始数据目录不存在: {cls.RAW_DATA_DIR}")

        return True


class DevelopmentConfig(Config):
    """开发环境配置"""
    ENV = 'development'
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """生产环境配置"""
    ENV = 'production'
    DEBUG = False
    LOG_LEVEL = 'INFO'
    AUTO_CLEANUP = True
    # 生产环境应设置真实域名
    # SERVER_URL = 'https://api.yourdomain.com'


class TestingConfig(Config):
    """测试环境配置"""
    ENV = 'testing'
    TESTING = True
    DEBUG = True


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(env=None):
    """
    获取配置对象

    Args:
        env: 环境名称 ('development', 'production', 'testing')

    Returns:
        Config对象
    """
    if env is None:
        env = os.getenv('FLASK_ENV', 'development')

    return config.get(env, config['default'])