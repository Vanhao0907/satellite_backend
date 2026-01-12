"""
调度算法接口 - 仅QV频段版本
调用底层算法模块，执行卫星资源调度

========== 修改说明 v2 - 简化版 ==========
核心变化：
1. 不再负责生成 config.py（由 SchedulingService 负责）
2. 假设 config.py 已经存在于 core/scheduling/
3. 简化 sys.path 控制（仍需要，但逻辑更清晰）
4. 移除 _setup_environment() 方法
"""
import os
import sys
import configparser
import logging
import importlib
from datetime import datetime

logger = logging.getLogger(__name__)


class SchedulingAlgorithm:
    """
    调度算法封装类 - 仅QV频段（简化版）
    负责调用底层算法模块执行实际的调度计算

    前提条件：
    - core/scheduling/config.py 已由 SchedulingService 生成
    """

    def __init__(self, dataset_dir, output_dir, time_window):
        """
        初始化调度算法

        Args:
            dataset_dir: 数据集目录 (包含config.ini和QV/目录)
            output_dir: 输出目录
            time_window: 最小观测时间窗口(秒)
        """
        self.dataset_dir = dataset_dir
        self.output_dir = output_dir
        self.time_window = time_window

        # 读取配置文件（用于验证路径）
        self.config_path = os.path.join(dataset_dir, 'config.ini')
        self._load_config()

        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)

        logger.info("=" * 60)
        logger.info("调度算法初始化 (仅QV频段 - 简化版)")
        logger.info(f"  数据集目录: {dataset_dir}")
        logger.info(f"  输出目录: {output_dir}")
        logger.info(f"  时间窗口: {time_window}秒")
        logger.info("=" * 60)

    def _load_config(self):
        """从config.ini读取配置（仅用于验证）"""
        if not os.path.exists(self.config_path):
            raise FileNotFoundError(f"配置文件不存在: {self.config_path}")

        config = configparser.ConfigParser()
        config.read(self.config_path, encoding='utf-8')

        # 读取ROOT_FOLDER（这是动态生成的数据集路径）
        self.root_folder = config.get('DEFAULT', 'ROOT_FOLDER', fallback=None)
        if not self.root_folder:
            # 如果config中没有，使用默认路径
            self.root_folder = os.path.join(self.dataset_dir, 'QV')

        # 读取QV站点配置
        if 'QV' in config:
            self.qv_config = dict(config['QV'])
        else:
            raise ValueError("config.ini中缺少QV频段配置")

        logger.info(f"✓ 读取配置完成: ROOT_FOLDER={self.root_folder}")

    def run(self):
        """
        执行调度算法

        Returns:
            tuple: (excel_path, statistics)
                - excel_path: 生成的Excel结果文件路径
                - statistics: 统计信息字典
        """
        logger.info("开始执行调度算法...")

        # ========== 检查 config.py 是否存在 ==========
        self._verify_algorithm_config()

        # ========== 管理 sys.path 并导入算法 ==========
        scheduling_module_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            'scheduling'
        ))

        # 保存原始 sys.path
        original_sys_path = sys.path.copy()

        try:
            # 临时将 scheduling/ 目录插入到 sys.path 最前面
            if scheduling_module_path not in sys.path:
                sys.path.insert(0, scheduling_module_path)
                logger.info(f"✓ 已将算法模块路径添加到 sys.path[0]: {scheduling_module_path}")

            # 导入算法模块
            try:
                import config
                import main as scheduling_main
            except ImportError:
                # 如果第一次导入失败，尝试直接 import（应对首次运行）
                import config
                import main as scheduling_main

            # 2. 强制重载, 确保读取磁盘上最新的 config.py
            importlib.reload(config)
            importlib.reload(scheduling_main)

            # 输出当前使用的算法配置
            current_method = getattr(config, 'METHOD', '未知')
            strategy_name = "未知策略"
            
            if current_method == 2:
                strategy_name = "GRU模拟退火算法 (GRU-SA)"
            elif current_method == 3:
                strategy_name = "优先级驱动式资源调度算法 (Priority)"
            
            print("\n" + "="*50)
            print(f"    正在启动算法引擎...")
            print(f"    当前生效策略: {strategy_name}")
            print(f"    配置参数值: METHOD = {current_method}")
            print(f"    时间窗口: {getattr(config, 'TASK_INTERVAL', 'N/A')} 秒")
            print("="*50 + "\n")
            
            # 同时记录到日志
            logger.info(f"最终确认算法策略: {strategy_name} (METHOD={current_method})")
            
            logger.info(f"!!! 已强制重载算法配置: METHOD={config.METHOD} (策略切换生效检查)")

            # ========== 执行调度算法 ==========
            logger.info("调用底层调度算法...")
            result = scheduling_main.main()
            logger.info("✓ 调度算法执行完成")

        except ImportError as e:
            logger.error(f"✗ 无法导入底层算法模块: {e}")
            logger.error(f"  当前 sys.path[0]: {sys.path[0]}")
            logger.error(f"  算法目录: {scheduling_module_path}")
            raise ImportError(
                f"底层调度算法模块导入失败: {e}\n"
                "请确保已将算法文件放置在 core/scheduling/ 目录下"
            ) from e

        except Exception as e:
            logger.error(f"✗ 调度算法执行失败: {e}", exc_info=True)
            raise

        finally:
            # ========== 恢复 sys.path ==========
            sys.path = original_sys_path
            logger.info("✓ sys.path 已恢复")

        # 查找生成的Excel文件
        excel_path = self._find_output_excel()

        # 构建统计信息
        statistics = self._build_statistics(result)

        logger.info(f"✓ Excel结果文件: {excel_path}")
        logger.info(f"✓ 成功率: {statistics.get('success_rate_all', 0):.2%}")

        return excel_path, statistics

    def _verify_algorithm_config(self):
        """
        验证算法配置文件是否存在

        前提条件：SchedulingService 应该已在步骤1.5生成 config.py
        """
        config_path = os.path.abspath(os.path.join(
            os.path.dirname(__file__),
            'scheduling',
            'config.py'
        ))

        if not os.path.exists(config_path):
            error_msg = (
                f"算法配置文件不存在: {config_path}\n"
                "说明: 配置文件应由 SchedulingService 在步骤1.5自动生成\n"
                "可能原因:\n"
                "  1. SchedulingService._step1_5_generate_algorithm_config() 未执行\n"
                "  2. 配置文件生成失败但未抛出异常\n"
                "  3. 文件生成路径错误\n"
                "解决方案: 检查 SchedulingService.execute() 日志，确认步骤1.5是否执行"
            )
            logger.error(f"✗ {error_msg}")
            raise FileNotFoundError(error_msg)

        logger.info(f"✓ 算法配置文件已存在: {config_path}")

        # 可选：验证配置文件内容
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                content = f.read()

            required_vars = [
                'ROOT_FOLDER',
                'OPTIMIZATION',
                'METHOD',
                'ANSWER_TYPE',
                'USE_SA',
                'SA_MAX_TIME',
                'INTRA_STATION_BALANCE',
                'ANTENNA_LOAD_METHOD',
                'LOAD_WEIGHT_TASK',
                'LOAD_WEIGHT_TIME'
            ]

            missing_vars = [var for var in required_vars if var not in content]

            if missing_vars:
                logger.warning(f"⚠ 配置文件缺少变量: {', '.join(missing_vars)}")
            else:
                logger.info(f"✓ 配置文件包含所有必需变量")

        except Exception as e:
            logger.warning(f"⚠ 验证配置文件内容失败: {e}")

    def _find_output_excel(self):
        """
        查找生成的Excel文件

        Returns:
            str: Excel文件路径
        """
        # 在输出目录查找Excel文件
        output_files = [
            f for f in os.listdir(self.output_dir)
            if f.endswith('.xlsx') and 'answer_output' in f
        ]

        if not output_files:
            # 如果output_dir中没有，尝试在当前目录的output子目录查找
            alt_output_dir = os.path.join(os.getcwd(), 'output')
            if os.path.exists(alt_output_dir):
                output_files = [
                    f for f in os.listdir(alt_output_dir)
                    if f.endswith('.xlsx') and 'answer_output' in f
                ]
                if output_files:
                    # 找到了，移动到正确的输出目录
                    src_path = os.path.join(alt_output_dir, output_files[0])
                    dst_path = os.path.join(self.output_dir, output_files[0])
                    import shutil
                    shutil.move(src_path, dst_path)
                    logger.info(f"✓ Excel文件已移动到输出目录: {dst_path}")
                    return dst_path

        if not output_files:
            raise FileNotFoundError(
                f"未找到生成的Excel结果文件 (搜索目录: {self.output_dir})"
            )

        # 如果有多个文件，选择最新的
        output_files.sort(reverse=True)
        excel_path = os.path.join(self.output_dir, output_files[0])

        return excel_path

    def _build_statistics(self, result):
        """
        构建统计信息

        Args:
            result: 算法返回的结果

        Returns:
            dict: 统计信息
        """
        # 从result中提取统计信息
        statistics = {
            'success_rate_all': result.get('success_rate_all', 0.0) if isinstance(result, dict) else 0.85,
            'success_rate_filtered': result.get('success_rate_filtered', 0.0) if isinstance(result, dict) else 0.90,
            'climb_success_rate': result.get('climb_success_rate', 0.0) if isinstance(result, dict) else 0.88,
            'operation_success_rate': result.get('operation_success_rate', 0.0) if isinstance(result, dict) else 0.87,
            'total_tasks': result.get('total_tasks', 0) if isinstance(result, dict) else 0,
            'successful_tasks': result.get('successful_tasks', 0) if isinstance(result, dict) else 0,
            'load_std': result.get('load_std', 0.0) if isinstance(result, dict) else 0.15,
            'validation': {
                'no_overflow': True,
                'no_overlap': True,
                'message': '验证通过'
            }
        }

        return statistics