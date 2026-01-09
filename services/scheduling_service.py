"""
卫星资源调度服务 - 仅QV频段版本（支持图片导出 + 算法选择 + 数据集统计 + ZIP下载）
串联所有处理步骤：数据集构建 → 统计信息 → 压缩ZIP → 调度算法 → 结果合并 → 可视化（HTML + 图片）
"""
import os
import shutil
import time
import logging
import zipfile
from datetime import datetime
from flask import current_app

from core.dataset_builder import DatasetBuilder
from core.scheduling_algorithm import SchedulingAlgorithm
from core.result_combiner import ResultCombiner
from core.gantt_chart_generator import GanttChartGenerator
from core.satisfaction_chart_generator import SatisfactionChartGenerator
from core.dataset_statistics import DatasetStatistics

logger = logging.getLogger(__name__)


class SchedulingService:
    """
    卫星资源调度服务 - 仅QV频段（支持HTML + 图片导出 + 算法选择 + 统计 + ZIP下载）
    负责协调整个调度流程
    """

    def __init__(self, params):
        """
        初始化服务

        Args:
            params: dict {
                "arc_data": str,
                "antenna_num": dict,
                "strategy": str,
                "time_window": int
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
        logger.info(f"[{self.task_id}] 算法策略: {params['strategy']}")
        logger.info(f"[{self.task_id}] 时间窗口: {params['time_window']}秒")

    def execute(self):
        """
        执行完整的调度流程（支持图片导出、算法选择、统计信息、ZIP下载）

        Returns:
            dict: {
                "task_id": str,
                "elapsed_time": float,
                "statistics": dict (包含站点统计和卫星类型统计),
                "charts": {
                    "gantt_chart_html": str,
                    "gantt_chart_image_url": str,
                    "satisfaction_chart_html": str,
                    "satisfaction_chart_image_url": str
                },
                "dataset_zip_url": str,
                "validation": dict
            }
        """
        start_time = time.time()

        try:
            logger.info(f"[{self.task_id}] ========== 开始执行调度流程 (仅QV频段) ==========")

            # 步骤1: 构建数据集
            dataset_path = self._step1_build_dataset()

            # 步骤1.5: 统计数据集信息
            dataset_stats = self._step1_5_calculate_statistics(dataset_path)

            # 步骤1.6: 压缩数据集为ZIP
            dataset_zip_url = self._step1_6_create_dataset_zip(dataset_path)

            # 步骤1.7: 生成算法配置文件
            self._step1_7_generate_algorithm_config(dataset_path)

            # 步骤2: 执行调度算法
            excel_path, statistics = self._step2_run_scheduling(dataset_path)

            # 步骤3: 合并结果
            result_dataset_path = self._step3_combine_results(dataset_path, excel_path)

            # 步骤4: 生成甘特图（HTML + 图片）
            gantt_html, gantt_image_url = self._step4_generate_gantt_chart(result_dataset_path)

            # 步骤5: 生成满足度分析图（HTML + 图片）
            satisfaction_html, satisfaction_image_url = self._step5_generate_satisfaction_chart(result_dataset_path)

            # 计算总耗时
            elapsed_time = time.time() - start_time

            # 合并统计信息（算法统计 + 数据集统计）
            combined_statistics = {**statistics, **dataset_stats}

            # 组装返回结果
            result = {
                'task_id': self.task_id,
                'elapsed_time': round(elapsed_time, 2),
                'statistics': combined_statistics,
                'charts': {
                    'gantt_chart_html': gantt_html,
                    'gantt_chart_image_url': gantt_image_url,
                    'satisfaction_chart_html': satisfaction_html,
                    'satisfaction_chart_image_url': satisfaction_image_url
                },
                'dataset_zip_url': dataset_zip_url,
                'validation': statistics.get('validation', {
                    'no_overflow': True,
                    'no_overlap': True,
                    'message': '验证通过'
                })
            }

            logger.info(f"[{self.task_id}] ========== 调度流程完成 ==========")
            logger.info(f"[{self.task_id}] 总耗时: {elapsed_time:.2f}秒")
            logger.info(f"[{self.task_id}] 成功率: {statistics.get('success_rate_all', 0):.2%}")
            logger.info(f"[{self.task_id}] 甘特图URL: {gantt_image_url}")
            logger.info(f"[{self.task_id}] 满足度图URL: {satisfaction_image_url}")
            logger.info(f"[{self.task_id}] 数据集ZIP URL: {dataset_zip_url}")
            logger.info(f"[{self.task_id}] 站点数据量: {dataset_stats['station_data_counts']}")
            logger.info(f"[{self.task_id}] 卫星类型统计: {dataset_stats['satellite_type_counts']}")

            # 可选：自动清理临时文件（保留静态图片和ZIP）
            if current_app.config.get('AUTO_CLEANUP', False):
                self._cleanup()

            return result

        except Exception as e:
            logger.error(f"[{self.task_id}] 执行失败: {str(e)}", exc_info=True)
            # 失败时清理临时文件
            self._cleanup()
            raise

    def _step1_build_dataset(self):
        """步骤1: 构建数据集"""
        logger.info(f"[{self.task_id}] 【步骤1/7】构建数据集 (仅QV频段)...")

        builder = DatasetBuilder(
            raw_data_dir=self.raw_data_dir,
            output_dir=self.dataset_dir,
            antenna_config=self.params['antenna_num']
        )

        dataset_path = builder.build()

        logger.info(f"[{self.task_id}] 数据集构建完成: {dataset_path}")
        return dataset_path

    def _step1_5_calculate_statistics(self, dataset_path):
        """步骤1.5: 统计数据集信息"""
        logger.info(f"[{self.task_id}] 【步骤1.5/7】统计数据集信息...")

        stats_calculator = DatasetStatistics(
            dataset_dir=dataset_path,
            antenna_config=self.params['antenna_num']
        )

        dataset_stats = stats_calculator.calculate()

        logger.info(f"[{self.task_id}] 数据集统计完成:")
        logger.info(f"[{self.task_id}]   站点数据量: {dataset_stats['station_data_counts']}")
        logger.info(f"[{self.task_id}]   卫星类型统计: {dataset_stats['satellite_type_counts']}")
        logger.info(f"[{self.task_id}]   总任务数（去重）: {dataset_stats['total_unique_tasks']}")

        return dataset_stats

    def _step1_6_create_dataset_zip(self, dataset_path):
        """步骤1.6: 压缩数据集为ZIP文件"""
        logger.info(f"[{self.task_id}] 【步骤1.6/7】压缩数据集为ZIP...")

        try:
            # 获取配置
            static_dir = current_app.config['STATIC_FILES_DIR']
            server_url = current_app.config['SERVER_URL']
            static_prefix = current_app.config['STATIC_URL_PREFIX']

            # 确保静态目录存在
            os.makedirs(static_dir, exist_ok=True)

            # 生成ZIP文件名
            zip_filename = f"{self.task_id}_dataset.zip"
            zip_filepath = os.path.join(static_dir, zip_filename)

            logger.info(f"[{self.task_id}]   目标ZIP路径: {zip_filepath}")

            # 创建ZIP文件
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zipf:
                # 遍历dataset目录下的所有文件
                for root, dirs, files in os.walk(dataset_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # 计算相对路径（保持目录结构）
                        arcname = os.path.relpath(file_path, dataset_path)
                        zipf.write(file_path, arcname)
                        logger.debug(f"[{self.task_id}]     添加文件: {arcname}")

            # 获取ZIP文件大小
            zip_size = os.path.getsize(zip_filepath)
            zip_size_mb = zip_size / (1024 * 1024)

            # 构建下载URL
            zip_url = f"{server_url}{static_prefix}/{zip_filename}"

            logger.info(f"[{self.task_id}] ✓ ZIP文件创建成功")
            logger.info(f"[{self.task_id}]   文件大小: {zip_size_mb:.2f} MB")
            logger.info(f"[{self.task_id}]   下载URL: {zip_url}")

            return zip_url

        except Exception as e:
            logger.error(f"[{self.task_id}] ZIP创建失败: {e}", exc_info=True)
            return None

    def _step1_7_generate_algorithm_config(self, dataset_path):
        """步骤1.7: 生成算法配置文件（支持算法选择）"""
        logger.info(f"[{self.task_id}] 【步骤1.7/7】生成算法配置文件...")

        try:
            project_root = os.getcwd()
            config_dir = os.path.join(project_root, 'core', 'scheduling')
            config_path = os.path.join(config_dir, 'config.py')

            logger.info(f"[{self.task_id}]   项目根目录: {project_root}")
            logger.info(f"[{self.task_id}]   目标配置目录: {config_dir}")
            logger.info(f"[{self.task_id}]   目标配置文件: {config_path}")

            if not os.path.exists(config_dir):
                logger.info(f"[{self.task_id}]   创建配置目录...")
                os.makedirs(config_dir, exist_ok=True)
                logger.info(f"[{self.task_id}]   ✓ 配置目录已创建")
            else:
                logger.info(f"[{self.task_id}]   ✓ 配置目录已存在")

            root_folder = os.path.join(dataset_path, 'QV')
            time_window = self.params['time_window']
            strategy = self.params['strategy']

            # ========== 功能一：根据策略选择METHOD ==========
            if strategy == "优先级驱动式资源调度算法":
                method_value = 3
                logger.info(f"[{self.task_id}]   算法策略: 优先级驱动式 (METHOD=3)")
            elif strategy == "GRU模拟退火算法":
                method_value = 2
                logger.info(f"[{self.task_id}]   算法策略: GRU模拟退火 (METHOD=2)")
            else:
                # 默认值
                method_value = 3
                logger.warning(f"[{self.task_id}]   未知策略'{strategy}'，使用默认值 METHOD=3")

            config_content = f"""# 算法配置文件 - 自动生成
# 任务ID: {self.task_id}
# 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
# 算法策略: {strategy}

ROOT_FOLDER = r'{root_folder}'
OPTIMIZATION = 'TRUE'
METHOD = {method_value}
ANSWER_TYPE = 'TRUE'
TASK_INTERVAL = {time_window}
USE_SA = 'FALSE'
SA_MAX_TIME = 300

INTRA_STATION_BALANCE = 'FALSE'
ANTENNA_LOAD_METHOD = 'B'
LOAD_WEIGHT_TASK = 0.3
LOAD_WEIGHT_TIME = 0.7
"""

            logger.info(f"[{self.task_id}]   正在写入配置文件...")

            with open(config_path, 'w', encoding='utf-8') as f:
                f.write(config_content)

            logger.info(f"[{self.task_id}]   ✓ 文件写入完成")

            if os.path.exists(config_path):
                file_size = os.path.getsize(config_path)
                logger.info(f"[{self.task_id}]   ✓ 验证通过: 文件存在，大小 {file_size} 字节")
                logger.info(f"[{self.task_id}] ✓ 算法配置文件生成成功!")
                self.algorithm_config_path = config_path
            else:
                error_msg = f"配置文件写入后仍不存在: {config_path}"
                logger.error(f"[{self.task_id}]   ✗ {error_msg}")
                raise FileNotFoundError(error_msg)

        except Exception as e:
            logger.error(f"[{self.task_id}] ✗ 生成配置文件失败: {e}", exc_info=True)
            raise RuntimeError(f"无法生成算法配置文件: {e}") from e

    def _step2_run_scheduling(self, dataset_path):
        """步骤2: 执行调度算法"""
        logger.info(f"[{self.task_id}] 【步骤2/7】执行调度算法...")

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
        """步骤3: 合并结果"""
        logger.info(f"[{self.task_id}] 【步骤3/7】合并结果数据...")

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
        步骤4: 生成甘特图（HTML + 图片）

        Returns:
            tuple: (html_content, image_url)
        """
        logger.info(f"[{self.task_id}] 【步骤4/7】生成甘特图（HTML + 图片）...")

        generator = GanttChartGenerator(
            result_dir=result_dataset_path,
            output_dir=self.charts_dir
        )

        gantt_html, gantt_image_url = generator.generate(self.task_id)

        logger.info(f"[{self.task_id}] 甘特图生成完成")
        logger.info(f"[{self.task_id}]   HTML长度: {len(gantt_html)} 字符")
        logger.info(f"[{self.task_id}]   图片URL: {gantt_image_url}")

        return gantt_html, gantt_image_url

    def _step5_generate_satisfaction_chart(self, result_dataset_path):
        """
        步骤5: 生成满足度分析图（HTML + 图片）

        Returns:
            tuple: (html_content, image_url)
        """
        logger.info(f"[{self.task_id}] 【步骤5/7】生成满足度分析图（HTML + 图片）...")

        generator = SatisfactionChartGenerator(
            result_dir=result_dataset_path,
            output_dir=self.charts_dir
        )

        satisfaction_html, satisfaction_image_url = generator.generate(self.task_id)

        logger.info(f"[{self.task_id}] 满足度图生成完成")
        logger.info(f"[{self.task_id}]   HTML长度: {len(satisfaction_html)} 字符")
        logger.info(f"[{self.task_id}]   图片URL: {satisfaction_image_url}")

        return satisfaction_html, satisfaction_image_url

    def _generate_task_id(self):
        """生成任务ID"""
        return f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

    def _create_directories(self):
        """创建必要的目录"""
        for directory in [self.dataset_dir, self.output_dir,
                         self.result_dir, self.charts_dir]:
            os.makedirs(directory, exist_ok=True)

    def _cleanup(self):
        """清理临时文件（保留静态图片和ZIP）"""
        logger.info(f"[{self.task_id}] 清理临时工作目录...")

        try:
            # 清理临时工作目录
            if os.path.exists(self.work_dir):
                shutil.rmtree(self.work_dir)
                logger.info(f"[{self.task_id}] ✓ 临时工作目录已清理: {self.work_dir}")

            # 清理算法配置文件（可选）
            if hasattr(self, 'algorithm_config_path') and os.path.exists(self.algorithm_config_path):
                os.remove(self.algorithm_config_path)
                logger.info(f"[{self.task_id}] ✓ 算法配置文件已清理")

            # 注意：静态图片和ZIP文件保留在 STATIC_FILES_DIR 中
            logger.info(f"[{self.task_id}] ℹ️  静态文件（图片和ZIP）已保留在静态目录")

        except Exception as e:
            logger.warning(f"[{self.task_id}] ⚠ 清理失败: {str(e)}")