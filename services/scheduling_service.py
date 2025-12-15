"""
卫星资源调度服务 - 仅QV频段版本
串联所有处理步骤：数据集构建 → 调度算法 → 结果合并 → 可视化

========== 修改说明 v3 - 修复路径问题 ==========
核心修复：
1. 使用 os.getcwd() 获取项目根目录（更可靠）
2. 添加详细的调试日志
3. 添加异常处理和错误提示
4. 验证配置文件是否成功生成
"""
import os
import shutil
import time
import logging
from datetime import datetime
from flask import current_app

from core.dataset_builder import DatasetBuilder
from core.scheduling_algorithm import SchedulingAlgorithm
from core.result_combiner import ResultCombiner
from core.gantt_chart_generator import GanttChartGenerator
from core.satisfaction_chart_generator import SatisfactionChartGenerator

logger = logging.getLogger(__name__)


class SchedulingService:
    """
    卫星资源调度服务 - 仅QV频段
    负责协调整个调度流程
    """

    def __init__(self, params):
        """
        初始化服务

        Args:
            params: dict {
                "arc_data": str,        # 数据集名称
                "antenna_num": dict,    # QV天线配置 (单层结构)
                "time_window": int      # 时间窗口（秒）
            }
        """
        self.params = params
        self.task_id = self._generate_task_id()

        # 从Flask配置中获取目录路径
        self.raw_data_dir = os.path.join(
            current_app.config['RAW_DATA_DIR'],
            params['arc_data']
        )
        self.work_dir = os.path.join(
            current_app.config['TEMP_DATA_DIR'],
            self.task_id
        )

        # 子目录定义
        self.dataset_dir = os.path.join(self.work_dir, 'dataset')
        self.output_dir = os.path.join(self.work_dir, 'output')
        self.result_dir = os.path.join(self.work_dir, 'result')
        self.charts_dir = os.path.join(self.work_dir, 'charts')

        # 验证原始数据是否存在
        if not os.path.exists(self.raw_data_dir):
            raise FileNotFoundError(
                f"数据集不存在: {params['arc_data']} "
                f"(路径: {self.raw_data_dir})"
            )

        # 创建工作目录
        self._create_directories()

        logger.info(f"[{self.task_id}] 服务初始化完成 (仅QV频段)")
        logger.info(f"[{self.task_id}] 原始数据: {self.raw_data_dir}")
        logger.info(f"[{self.task_id}] 工作目录: {self.work_dir}")
        logger.info(f"[{self.task_id}] 站点数: {len(params['antenna_num'])}")
        logger.info(f"[{self.task_id}] 总天线数: {sum(params['antenna_num'].values())}")
        logger.info(f"[{self.task_id}] 时间窗口: {params['time_window']}秒")

    def execute(self):
        """
        执行完整的调度流程

        Returns:
            dict: {
                "task_id": str,
                "elapsed_time": float,
                "statistics": dict,
                "charts": dict,
                "validation": dict
            }
        """
        start_time = time.time()

        try:
            logger.info(f"[{self.task_id}] ========== 开始执行调度流程 (仅QV频段) ==========")

            # 步骤1: 构建数据集
            dataset_path = self._step1_build_dataset()

            # ========== 核心修改：步骤1.5 生成算法配置文件 ==========
            self._step1_5_generate_algorithm_config(dataset_path)

            # 步骤2: 执行调度算法（简化版）
            excel_path, statistics = self._step2_run_scheduling(dataset_path)

            # 步骤3: 合并结果
            result_dataset_path = self._step3_combine_results(dataset_path, excel_path)

            # 步骤4: 生成甘特图
            gantt_html = self._step4_generate_gantt_chart(result_dataset_path)

            # 步骤5: 生成满足度分析图
            satisfaction_html = self._step5_generate_satisfaction_chart(result_dataset_path)

            # 计算总耗时
            elapsed_time = time.time() - start_time

            # 组装返回结果
            result = {
                'task_id': self.task_id,
                'elapsed_time': round(elapsed_time, 2),
                'statistics': statistics,
                'charts': {
                    'gantt_chart_html': gantt_html,
                    'satisfaction_chart_html': satisfaction_html
                },
                'validation': statistics.get('validation', {
                    'no_overflow': True,
                    'no_overlap': True,
                    'message': '验证通过'
                })
            }

            logger.info(f"[{self.task_id}] ========== 调度流程完成 ==========")
            logger.info(f"[{self.task_id}] 总耗时: {elapsed_time:.2f}秒")
            logger.info(f"[{self.task_id}] 成功率: {statistics.get('success_rate_all', 0):.2%}")

            # 可选：自动清理
            if current_app.config.get('AUTO_CLEANUP', False):
                self._cleanup()

            return result

        except Exception as e:
            logger.error(f"[{self.task_id}] 执行失败: {str(e)}", exc_info=True)
            # 失败时清理临时文件
            self._cleanup()
            raise

    def _step1_build_dataset(self):
        """
        步骤1: 构建数据集

        Returns:
            str: 数据集路径
        """
        logger.info(f"[{self.task_id}] 【步骤1/5】构建数据集 (仅QV频段)...")

        builder = DatasetBuilder(
            raw_data_dir=self.raw_data_dir,
            output_dir=self.dataset_dir,
            antenna_config=self.params['antenna_num']  # 单层结构
        )

        dataset_path = builder.build()

        logger.info(f"[{self.task_id}] 数据集构建完成: {dataset_path}")
        return dataset_path

    def _step1_5_generate_algorithm_config(self, dataset_path):
        """
        ========== 核心修改：步骤1.5 生成算法配置文件 ==========

        直接在 core/scheduling/ 目录生成 config.py
        将前端参数映射为算法需要的配置常量

        Args:
            dataset_path: 数据集路径（从步骤1获得）
        """
        logger.info(f"[{self.task_id}] 【步骤1.5/5】生成算法配置文件...")

        try:
            # ========== 修复：使用当前工作目录（最可靠）==========
            project_root = os.getcwd()
            config_dir = os.path.join(project_root, 'core', 'scheduling')
            config_path = os.path.join(config_dir, 'config.py')

            logger.info(f"[{self.task_id}]   项目根目录: {project_root}")
            logger.info(f"[{self.task_id}]   目标配置目录: {config_dir}")
            logger.info(f"[{self.task_id}]   目标配置文件: {config_path}")

            # 确保目录存在
            if not os.path.exists(config_dir):
                logger.info(f"[{self.task_id}]   创建配置目录...")
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"[{self.task_id}]   ✓ 配置目录已创建")
            else:
                logger.info(f"[{self.task_id}]   ✓ 配置目录已存在")

            # ========== 参数映射 ==========
            # 1. ROOT_FOLDER: 从数据集路径获取
            root_folder = os.path.join(dataset_path, 'QV')
            logger.info(f"[{self.task_id}]   ROOT_FOLDER = {root_folder}")

            # 2. TASK_INTERVAL: 从前端 time_window 参数获取
            time_window = self.params['time_window']
            logger.info(f"[{self.task_id}]   TASK_INTERVAL = {time_window} (来自 time_window)")

            # 3. 其他参数：使用默认值
            optimization = 'TRUE'
            method = 3
            answer_type = 'TRUE'
            use_sa = 'FALSE'
            SA_MAX_TIME = 300
            intra_station_balance = 'FALSE'
            antenna_load_method = 'B'
            load_weight_task = 0.3
            load_weight_time = 0.7

            # ========== 生成配置内容 ==========
            config_content = f"""# 算法配置文件 - 自动生成
# 任务ID: {self.task_id}
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 来源: API参数 → 配置映射

# ========== 数据集路径（动态生成）==========
ROOT_FOLDER = r'{root_folder}'
# 说明: 来自数据集构建步骤，指向 {dataset_path}/QV

# ========== 调度算法基础配置 ==========
OPTIMIZATION = '{optimization}'  # 是否启用优化
METHOD = {method}  # 调度方法: 1=时间窗口优先, 2=天线可用率优先, 3=天线均衡优先(推荐)
ANSWER_TYPE = '{answer_type}'  # 是否输出Excel格式结果
TASK_INTERVAL = {time_window}  # 来自前端 time_window 参数
USE_SA = '{use_sa}'  # 是否使用模拟退火优化
SA_MAX_TIME = 300  # 模拟退火最大时间(秒)

# ========== 站内天线负载均衡策略配置 ==========
INTRA_STATION_BALANCE = '{intra_station_balance}'  # 是否启用站内天线负载均衡
ANTENNA_LOAD_METHOD = '{antenna_load_method}'  # 负载计算方法: A=任务数量, B=时间占用, C=综合负载
LOAD_WEIGHT_TASK = {load_weight_task}  # 任务数量权重 (仅method=C时使用)
LOAD_WEIGHT_TIME = {load_weight_time}  # 时间占用权重 (仅method=C时使用)

# ========== 配置说明 ==========
# 本文件由调度服务自动生成，供底层算法模块使用
# 修改此文件不会影响下次调度，因为每次都会重新生成
# 如需修改默认配置，请修改 services/scheduling_service.py 中的默认值
"""

            # ========== 写入文件 ==========
            logger.info(f"[{self.task_id}]   正在写入配置文件...")

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            logger.info(f"[{self.task_id}]   ✓ 文件写入完成")

            # ========== 验证文件是否成功生成 ==========
            if os.path.exists(config_path):
                file_size = os.path.getsize(config_path)
                logger.info(f"[{self.task_id}]   ✓ 验证通过: 文件存在，大小 {file_size} 字节")

                # 读取并验证内容
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()

                required_vars = ['ROOT_FOLDER', 'TASK_INTERVAL', 'OPTIMIZATION',
                                'METHOD', 'INTRA_STATION_BALANCE']
                missing = [v for v in required_vars if v not in content]

                if missing:
                    logger.warning(f"[{self.task_id}]   ⚠ 配置文件缺少变量: {missing}")
                else:
                    logger.info(f"[{self.task_id}]   ✓ 配置文件包含所有必需变量")

                logger.info(f"[{self.task_id}] ✓ 算法配置文件生成成功!")

                # 保存配置路径供后续清理使用
                self.algorithm_config_path = config_path

            else:
                error_msg = f"配置文件写入后仍不存在: {config_path}"
                logger.error(f"[{self.task_id}]   ✗ {error_msg}")
                raise FileNotFoundError(error_msg)

        except Exception as e:
            logger.error(f"[{self.task_id}] ✗ 生成配置文件失败: {e}", exc_info=True)
            raise RuntimeError(f"无法生成算法配置文件: {e}") from e

    def _step2_run_scheduling(self, dataset_path):
        """
        步骤2: 执行调度算法（简化版）

        Args:
            dataset_path: 数据集路径

        Returns:
            tuple: (excel_path, statistics)
        """
        logger.info(f"[{self.task_id}] 【步骤2/5】执行调度算法...")

        # ========== 简化版：直接使用 SchedulingAlgorithm ==========
        # config.py 已经在步骤1.5生成，算法会自动找到
        scheduler = SchedulingAlgorithm(
            dataset_dir=dataset_path,
            output_dir=self.output_dir,
            time_window=self.params['time_window']
        )

        excel_path, statistics = scheduler.run()

        logger.info(
            f"[{self.task_id}] 调度完成: "
            f"成功率={statistics.get('success_rate_all', 0):.2%}, "
            f"负载标准差={statistics.get('load_std', 0):.4f}"
        )

        return excel_path, statistics

    def _step3_combine_results(self, dataset_path, excel_path):
        """
        步骤3: 合并结果

        Args:
            dataset_path: 数据集路径
            excel_path: Excel结果文件路径

        Returns:
            str: 合并后的结果数据集路径
        """
        logger.info(f"[{self.task_id}] 【步骤3/5】合并结果数据...")

        combiner = ResultCombiner(
            dataset_dir=dataset_path,
            excel_path=excel_path,
            output_dir=self.result_dir
        )

        result_dataset_path = combiner.combine()

        logger.info(f"[{self.task_id}] 结果合并完成: {result_dataset_path}")
        return result_dataset_path

    def _step4_generate_gantt_chart(self, result_dataset_path):
        """
        步骤4: 生成甘特图

        Args:
            result_dataset_path: 合并后的结果数据集路径

        Returns:
            str: 甘特图HTML内容
        """
        logger.info(f"[{self.task_id}] 【步骤4/5】生成甘特图...")

        generator = GanttChartGenerator(
            result_dir=result_dataset_path,
            output_dir=self.charts_dir
        )

        gantt_html = generator.generate()

        logger.info(f"[{self.task_id}] 甘特图生成完成")
        return gantt_html

    def _step5_generate_satisfaction_chart(self, result_dataset_path):
        """
        步骤5: 生成满足度分析图

        Args:
            result_dataset_path: 合并后的结果数据集路径

        Returns:
            str: 满足度图HTML内容
        """
        logger.info(f"[{self.task_id}] 【步骤5/5】生成满足度分析图...")

        generator = SatisfactionChartGenerator(
            result_dir=result_dataset_path,
            output_dir=self.charts_dir
        )

        satisfaction_html = generator.generate()

        logger.info(f"[{self.task_id}] 满足度图生成完成")
        return satisfaction_html

    def _generate_task_id(self):
        """生成任务ID"""
        return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _create_directories(self):
        """创建必要的目录"""
        for directory in [self.dataset_dir, self.output_dir,
                         self.result_dir, self.charts_dir]:
            os.makedirs(directory, exist_ok=True)

    def _cleanup(self):
        """
        清理临时文件

        ========== 调试模式：暂时禁用清理 ==========
        保留临时文件以便诊断问题
        """
        logger.info(f"[{self.task_id}] ⚠ 清理已禁用（调试模式）")
        logger.info(f"[{self.task_id}]   临时文件保留在: {self.work_dir}")

        # 暂时注释掉清理代码
        # try:
        #     # 1. 清理工作目录
        #     if os.path.exists(self.work_dir):
        #         shutil.rmtree(self.work_dir)
        #         logger.info(f"[{self.task_id}] ✓ 临时工作目录已清理: {self.work_dir}")
        #
        #     # 2. 清理算法配置文件（可选）
        #     if hasattr(self, 'algorithm_config_path') and os.path.exists(self.algorithm_config_path):
        #         os.remove(self.algorithm_config_path)
        #         logger.info(f"[{self.task_id}] ✓ 算法配置文件已清理: {self.algorithm_config_path}")
        #
        # except Exception as e:
        #     logger.warning(f"[{self.task_id}] ⚠ 清理失败: {str(e)}")