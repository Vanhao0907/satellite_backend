"""
卫星资源调度仿真API - 仅QV频段版本（支持图片导出）
提供单一接口：POST /api/simulations
"""
from flask import Blueprint, request, jsonify, current_app
from services.scheduling_service import SchedulingService
import logging

# 创建蓝图
simulation_bp = Blueprint('simulation', __name__)
logger = logging.getLogger(__name__)


@simulation_bp.route('/simulations', methods=['POST'])
def run_simulation():
    """
    执行卫星资源调度仿真 (仅QV频段，支持图片导出)

    请求示例:
    POST /api/simulations
    Content-Type: application/json

    {
        "arc_data": "access_1110to1210",
        "antenna_num": {
            "CM": 6,
            "JMS": 14,
            "KEL": 18,
            "KS": 5,
            "MH": 3,
            "TC": 10,
            "WC": 6,
            "XA": 8
        },
        "time_window": 300
    }

    返回示例:
    {
        "code": 200,
        "message": "卫星资源调度完成",
        "data": {
            "task_id": "task_20241212_134523",
            "elapsed_time": 287.5,
            "statistics": {...},
            "charts": {
                "gantt_chart_html": "<html>...</html>",
                "gantt_chart_image_url": "http://localhost:5000/static/task_xxx_gantt.jpeg",
                "satisfaction_chart_html": "<html>...</html>",
                "satisfaction_chart_image_url": "http://localhost:5000/static/task_xxx_satisfaction.jpeg"
            },
            "validation": {...}
        }
    }
    """
    logger.info(f"收到请求！来源IP: {request.remote_addr}")
    logger.info(f"请求数据: {request.get_json()}")
    try:
        # 1. 获取请求参数
        if not request.is_json:
            return jsonify({
                'code': 400,
                'message': '请求Content-Type必须为application/json',
                'data': None
            }), 400

        params = request.get_json()

        # 2. 验证必需参数
        required_fields = ['arc_data', 'antenna_num', 'time_window']
        missing_fields = [field for field in required_fields if field not in params]

        if missing_fields:
            return jsonify({
                'code': 400,
                'message': f'缺少必需参数: {", ".join(missing_fields)}',
                'data': None
            }), 400

        # 3. 参数类型验证
        if not isinstance(params['arc_data'], str):
            return jsonify({
                'code': 400,
                'message': 'arc_data必须为字符串',
                'data': None
            }), 400

        if not isinstance(params['antenna_num'], dict):
            return jsonify({
                'code': 400,
                'message': 'antenna_num必须为对象',
                'data': None
            }), 400

        # 验证antenna_num是单层结构（QV频段）
        for station, count in params['antenna_num'].items():
            if not isinstance(count, (int, float)) or count <= 0:
                return jsonify({
                    'code': 400,
                    'message': f'antenna_num.{station}必须为正数',
                    'data': None
                }), 400

        if not isinstance(params['time_window'], (int, float)):
            return jsonify({
                'code': 400,
                'message': 'time_window必须为数字',
                'data': None
            }), 400

        # 天线数量上限验证
        max_antennas = current_app.config.get('MAX_ANTENNAS_PER_STATION', 20)
        for station, count in params['antenna_num'].items():
            if count > max_antennas:
                return jsonify({
                    'code': 400,
                    'message': f'站点 {station} 的天线数量 {count} 超过系统最大限制 {max_antennas}',
                    'data': None
                }), 400

        # 记录请求日志
        logger.info(
            f"接收到调度请求: "
            f"arc_data={params['arc_data']}, "
            f"time_window={params['time_window']}, "
            f"stations={list(params['antenna_num'].keys())}, "
            f"total_antennas={sum(params['antenna_num'].values())}"
        )

        # 4. 调用业务逻辑服务
        service = SchedulingService(params)
        result = service.execute()

        # 5. 返回成功响应
        logger.info(f"调度完成: task_id={result['task_id']}, elapsed_time={result['elapsed_time']}s")
        logger.info(f"甘特图URL: {result['charts']['gantt_chart_image_url']}")
        logger.info(f"满足度图URL: {result['charts']['satisfaction_chart_image_url']}")

        return jsonify({
            'code': 200,
            'message': '卫星资源调度完成',
            'data': result
        }), 200

    except ValueError as e:
        # 参数验证错误
        logger.error(f"参数验证错误: {str(e)}")
        return jsonify({
            'code': 400,
            'message': str(e),
            'data': None
        }), 400

    except FileNotFoundError as e:
        # 文件不存在错误
        logger.error(f"文件未找到: {str(e)}")
        return jsonify({
            'code': 404,
            'message': f'数据集不存在: {str(e)}',
            'data': None
        }), 404

    except Exception as e:
        # 其他未预期错误
        logger.error(f"调度执行失败: {str(e)}", exc_info=True)
        return jsonify({
            'code': 500,
            'message': f'调度执行失败: {str(e)}',
            'data': None
        }), 500


@simulation_bp.route('/simulations/test', methods=['GET'])
def test_endpoint():
    """
    测试接口
    用于验证API是否正常工作
    """
    max_antennas = current_app.config.get('MAX_ANTENNAS_PER_STATION', 20)
    server_url = current_app.config.get('SERVER_URL', 'http://localhost:5000')

    return jsonify({
        'code': 200,
        'message': '仿真API工作正常',
        'data': {
            'endpoint': '/api/simulations',
            'method': 'POST',
            'status': 'available',
            'version': 'QV_ONLY_v2.1_with_image_export',  # ← 更新版本号
            'required_params': ['arc_data', 'antenna_num', 'time_window'],
            'max_antennas_per_station': max_antennas,
            'server_url': server_url,
            'static_url_prefix': current_app.config.get('STATIC_URL_PREFIX', '/static'),
            'features': ['HTML_Charts', 'Image_Export_JPEG']  # ← 新增
        }
    }), 200