"""
数据集构建器 - 仅QV频段版本
基于原始脚本: dataset.py
功能: 将原始Excel文件转换为算法所需的层次化CSV目录结构
"""
import os
import pandas as pd
import configparser
import shutil
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class DatasetBuilder:
    """
    数据集构建器 - 仅支持QV频段
    负责从原始Excel数据生成算法所需的CSV数据集
    """

    # QV频段站点顺序映射
    STATION_ORDER = {
        'CM': 1,
        'JMS': 2,
        'KEL': 3,
        'KS': 4,
        'MH': 5,
        'TC': 6,
        'WC': 7,
        'XA': 8
    }

    def __init__(self, raw_data_dir, output_dir, antenna_config):
        """
        初始化构建器

        Args:
            raw_data_dir: 原始数据目录 (如: data/raw/access_1110to1210)
            output_dir: 输出目录 (如: data/temp/task_xxx/dataset)
            antenna_config: 天线配置 (简化为单层结构)
                {
                    "CM": 6,
                    "JMS": 14,
                    "KEL": 18,
                    "KS": 5,
                    "MH": 3,
                    "TC": 10,
                    "WC": 6,
                    "XA": 8
                }
        """
        self.raw_data_dir = raw_data_dir
        self.output_dir = output_dir
        self.antenna_config = antenna_config

        logger.info(f"数据集构建器初始化 (仅QV频段): {raw_data_dir} -> {output_dir}")
        logger.info(f"天线配置: {antenna_config}")

    def build(self):
        """
        构建数据集

        Returns:
            str: 生成的数据集路径 (如: data/temp/task_xxx/dataset/access_251212_pro)
        """
        logger.info("=" * 60)
        logger.info("开始构建数据集 (仅QV频段)")
        logger.info("=" * 60)

        # 1. 生成数据集目录名
        dataset_name = self._generate_output_dirname()
        dataset_path = os.path.join(self.output_dir, dataset_name)

        # 2. 创建输出目录
        self._remove_and_create_dir(dataset_path)

        # 3. 生成config.ini文件
        config_path = self._generate_config(dataset_path)
        logger.info(f"✓ 配置文件已生成: {config_path}")

        # 4. 处理QV频段
        stats = self._process_qv_band(dataset_path)

        # 5. 打印统计信息
        logger.info("=" * 60)
        logger.info("数据集构建完成")
        logger.info(f"  生成文件数: {stats['success']}")
        logger.info(f"  失败文件数: {stats['fail']}")
        logger.info(f"  处理站点数: {stats['stations']}")
        logger.info(f"  输出目录: {dataset_path}")
        logger.info("=" * 60)

        return dataset_path

    def _generate_output_dirname(self):
        """
        根据当前日期生成输出目录名
        格式: access_YYMMDD_pro
        """
        current_date = datetime.now().strftime('%y%m%d')
        return f"access_{current_date}_pro"

    def _remove_and_create_dir(self, dir_path):
        """
        删除目录（如果存在）并重新创建
        """
        if os.path.exists(dir_path):
            logger.warning(f"⚠ 检测到输出目录已存在: {dir_path}")
            shutil.rmtree(dir_path)
            logger.info(f"✓ 旧目录已删除")

        os.makedirs(dir_path)
        logger.info(f"✓ 创建新目录: {dir_path}")

    def _generate_config(self, dataset_path):
        """
        生成config.ini配置文件 (仅QV频段)

        Args:
            dataset_path: 数据集路径

        Returns:
            str: 配置文件路径
        """
        config = configparser.ConfigParser()

        # 添加DEFAULT部分 - ROOT_FOLDER指向QV目录
        qv_folder_path = os.path.join(dataset_path, 'QV')
        config['DEFAULT'] = {
            'ROOT_FOLDER': qv_folder_path
        }

        # 添加QV站点配置
        config['QV'] = {}
        for station, antenna_count in self.antenna_config.items():
            config['QV'][station] = str(antenna_count)

        # 保存配置文件
        config_path = os.path.join(dataset_path, 'config.ini')
        with open(config_path, 'w', encoding='utf-8') as f:
            config.write(f)

        return config_path

    def _process_qv_band(self, dataset_path):
        """
        处理QV频段的所有站点

        Args:
            dataset_path: 数据集输出路径

        Returns:
            dict: 统计信息 {'success': int, 'fail': int, 'stations': int}
        """
        logger.info("")
        logger.info("=" * 60)
        logger.info("正在处理QV频段")
        logger.info("=" * 60)

        # 输入输出目录
        input_dir = os.path.join(self.raw_data_dir, 'QV')
        output_dir = os.path.join(dataset_path, 'QV')

        # 检查输入目录是否存在
        if not os.path.exists(input_dir):
            error_msg = f"QV频段输入目录不存在: {input_dir}"
            logger.error(f"✗ {error_msg}")
            raise FileNotFoundError(error_msg)

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)

        # 统计信息
        total_success = 0
        total_fail = 0
        processed_stations = 0

        # 按顺序处理每个站点
        for station_prefix, station_num in sorted(self.STATION_ORDER.items(), key=lambda x: x[1]):
            # 检查配置中是否有该站点
            if station_prefix not in self.antenna_config:
                logger.info(f"  ⊘ 跳过 {station_prefix}站 - 配置中未定义")
                continue

            # 获取天线数量
            antenna_count = self.antenna_config[station_prefix]

            # 处理该站点
            success, fail = self._process_station(
                input_dir, output_dir, station_prefix,
                station_num, antenna_count
            )

            total_success += success
            total_fail += fail
            processed_stations += 1

        logger.info("")
        logger.info(f"QV频段处理完成: 生成{total_success}个文件")

        return {
            'success': total_success,
            'fail': total_fail,
            'stations': processed_stations
        }

    def _process_station(self, input_dir, output_dir, station_prefix,
                        station_num, antenna_count):
        """
        处理单个站点的所有天线数据

        Args:
            input_dir: 输入目录
            output_dir: 输出目录
            station_prefix: 站点前缀（如CM）
            station_num: 站点编号
            antenna_count: 该站天线数量

        Returns:
            tuple: (成功数, 失败数)
        """
        success_count = 0
        fail_count = 0

        # 创建站点目录
        station_dir_path = os.path.join(output_dir, station_prefix)
        os.makedirs(station_dir_path, exist_ok=True)

        logger.info(f"  {station_prefix}站 ({antenna_count}根天线)")
        logger.info(f"    目录: {station_prefix}/")

        # 查找原始Excel文件
        excel_file = self._find_excel_file(input_dir, station_prefix)

        if excel_file is None:
            logger.error(f"    ✗ 错误: 未找到原始Excel文件 ({station_prefix}01_*_access.xlsx)")
            return 0, antenna_count

        # 读取Excel数据
        try:
            df = pd.read_excel(excel_file)
            logger.info(f"    ✓ 读取Excel文件: {os.path.basename(excel_file)}")
        except Exception as e:
            logger.error(f"    ✗ 错误: 读取Excel失败 - {e}")
            return 0, antenna_count

        # 检查sta字段是否存在
        has_sta_column = 'sta' in df.columns
        if not has_sta_column:
            logger.warning(f"    ⚠ 警告: Excel文件中缺少'sta'列")

        # 生成所有天线的CSV文件
        for antenna_num in range(1, antenna_count + 1):
            antenna_id = f"{station_prefix}{antenna_num:02d}"
            csv_filename = f"{antenna_id}_access.csv"
            csv_filepath = os.path.join(station_dir_path, csv_filename)

            # 复制数据
            new_df = df.copy()

            # 修改sta字段（如果存在）
            if has_sta_column:
                new_df['sta'] = antenna_id

            # 保存CSV文件
            try:
                new_df.to_csv(csv_filepath, index=False, encoding='utf-8')
                logger.info(f"    ✓ 生成: {csv_filename}")
                success_count += 1
            except Exception as e:
                logger.error(f"    ✗ 失败: {csv_filename} - {e}")
                fail_count += 1

        return success_count, fail_count

    def _find_excel_file(self, input_dir, station_prefix):
        """
        查找原始Excel文件

        Args:
            input_dir: 输入目录路径
            station_prefix: 站点前缀（如CM, JMS）

        Returns:
            str: Excel文件路径，如果不存在返回None
        """
        # 尝试多种可能的文件名格式
        possible_patterns = [
            f"{station_prefix}01_QV_access.xlsx",
            f"{station_prefix}01_access.xlsx",
            f"{station_prefix.lower()}01_qv_access.xlsx",
            f"{station_prefix.upper()}01_QV_access.xlsx"
        ]

        for pattern in possible_patterns:
            file_path = os.path.join(input_dir, pattern)
            if os.path.exists(file_path):
                return file_path

        return None