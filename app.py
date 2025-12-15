"""
Flask应用主入口
"""
from flask import Flask, jsonify
from flask_cors import CORS
import logging
from logging.handlers import RotatingFileHandler
import os

from config import get_config
from api.simulation_api import simulation_bp


def create_app(env=None):
    """
    应用工厂函数
    
    Args:
        env: 环境名称 ('development', 'production', 'testing')
    
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    config = get_config(env)
    app.config.from_object(config)
    
    # 确保目录存在
    config.ensure_directories()
    
    # 配置CORS
    CORS(app, origins=config.CORS_ORIGINS)
    
    # 配置日志
    setup_logging(app, config)
    
    # 注册蓝图
    app.register_blueprint(simulation_bp, url_prefix='/api')
    
    # 注册错误处理器
    register_error_handlers(app)
    
    # 注册健康检查路由
    @app.route('/')
    def index():
        return jsonify({
            'service': 'Satellite Scheduling Backend',
            'version': '1.0.0',
            'status': 'running'
        })
    
    @app.route('/health')
    def health_check():
        return jsonify({
            'status': 'healthy',
            'message': '服务运行正常'
        })
    
    app.logger.info('Flask应用初始化完成')
    
    return app


def setup_logging(app, config):
    """
    配置日志系统
    
    Args:
        app: Flask应用实例
        config: 配置对象
    """
    # 设置日志级别
    log_level = getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    
    # 创建日志格式
    formatter = logging.Formatter(
        '[%(asctime)s] %(levelname)s in %(module)s: %(message)s'
    )
    
    # 文件处理器（滚动日志）
    log_file = os.path.join(config.LOG_DIR, 'app.log')
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=config.LOG_MAX_BYTES,
        backupCount=config.LOG_BACKUP_COUNT
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(log_level)
    
    # 控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
    
    # 添加处理器到Flask logger
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(log_level)
    
    # 禁用werkzeug默认日志（避免重复）
    logging.getLogger('werkzeug').setLevel(logging.WARNING)


def register_error_handlers(app):
    """
    注册全局错误处理器
    
    Args:
        app: Flask应用实例
    """
    
    @app.errorhandler(400)
    def bad_request(e):
        app.logger.warning(f'Bad Request: {str(e)}')
        return jsonify({
            'code': 400,
            'message': '请求参数错误',
            'data': None
        }), 400
    
    @app.errorhandler(404)
    def not_found(e):
        app.logger.warning(f'Not Found: {str(e)}')
        return jsonify({
            'code': 404,
            'message': '请求的资源不存在',
            'data': None
        }), 404
    
    @app.errorhandler(500)
    def internal_server_error(e):
        app.logger.error(f'Internal Server Error: {str(e)}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': '服务器内部错误',
            'data': None
        }), 500
    
    @app.errorhandler(Exception)
    def handle_exception(e):
        app.logger.error(f'Unhandled Exception: {str(e)}', exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'服务器错误: {str(e)}',
            'data': None
        }), 500


if __name__ == '__main__':
    # 创建应用
    app = create_app()
    
    # 运行应用
    app.run(
        host=app.config['HOST'],
        port=app.config['PORT'],
        debug=app.config['DEBUG']
        #host='0.0.0.0',
        #port=5000,
        #debug=True
    )
