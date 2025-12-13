"""
卫星资源调度服务 - 仅QV频段版本
串联所有处理步骤：数据集构建 → 调度算法 → 结果合并 → 可视化
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
                "time_window": int      # 时间窗口
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

            # 步骤2: 执行调度算法
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

    def _step2_run_scheduling(self, dataset_path):
        """
        步骤2: 执行调度算法

        Args:
            dataset_path: 数据集路径

        Returns:
            tuple: (excel_path, statistics)
        """
        logger.info(f"[{self.task_id}] 【步骤2/5】执行调度算法...")

        # 只传递3个核心参数
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
        """清理临时文件"""
        try:
            if os.path.exists(self.work_dir):
                shutil.rmtree(self.work_dir)
                logger.info(f"[{self.task_id}] 临时文件已清理")
        except Exception as e:
            logger.warning(f"[{self.task_id}] 清理失败: {str(e)}")