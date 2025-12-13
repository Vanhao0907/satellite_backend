"""
结果合并器 - 修复版
原始脚本: 5result_combine.py
功能: 将算法输出的Excel结果与数据集CSV文件合并，生成最终的调度结果数据集

修复内容：
1. 避免重复添加 allocation_status 列
2. 处理 CSV 中已存在该列的情况
"""
import os
import logging
import pandas as pd
import shutil
import numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)


class ResultCombiner:
    """
    结果合并器
    将调度算法生成的Excel结果与原始CSV数据合并
    """

    def __init__(self, dataset_dir, excel_path, output_dir):
        """
        初始化合并器

        Args:
            dataset_dir: 数据集目录 (包含QV/子目录和CSV文件)
            excel_path: Excel结果文件路径 (算法生成的分配结果)
            output_dir: 输出目录 (合并后的结果输出路径)
        """
        self.dataset_dir = dataset_dir
        self.excel_path = excel_path
        self.output_dir = output_dir

        logger.info("=" * 60)
        logger.info("结果合并器初始化（修复版）")
        logger.info(f"  数据集目录: {dataset_dir}")
        logger.info(f"  Excel结果: {excel_path}")
        logger.info(f"  输出目录: {output_dir}")
        logger.info("=" * 60)

    def combine(self):
        """
        合并结果

        核心逻辑：
        1. 读取Excel分配结果
        2. 读取原始CSV数据
        3. 将分配状态添加到CSV中
        4. 生成合并后的结果数据集

        Returns:
            str: 合并后的结果数据集路径
        """
        logger.info("开始合并结果...")

        # 1. 创建输出目录
        result_path = os.path.join(self.output_dir, 'access_result')
        os.makedirs(result_path, exist_ok=True)

        # 2. 创建QV子目录
        qv_result_path = os.path.join(result_path, 'QV')
        os.makedirs(qv_result_path, exist_ok=True)

        # 3. 读取Excel结果文件
        logger.info("读取Excel分配结果...")
        try:
            excel_data = pd.read_excel(self.excel_path, sheet_name=None, engine='openpyxl')
            logger.info(f"✓ 成功读取Excel文件，包含 {len(excel_data)} 个工作表")
        except Exception as e:
            logger.error(f"✗ 读取Excel文件失败: {e}")
            raise

        # 4. 获取原始CSV数据目录
        qv_data_dir = os.path.join(self.dataset_dir, 'QV')

        if not os.path.exists(qv_data_dir):
            logger.error(f"✗ QV数据目录不存在: {qv_data_dir}")
            raise FileNotFoundError(f"QV数据目录不存在: {qv_data_dir}")

        # 5. 处理每个站点
        station_count = 0
        total_files = 0

        for station_name in sorted(os.listdir(qv_data_dir)):
            station_path = os.path.join(qv_data_dir, station_name)

            if not os.path.isdir(station_path):
                continue

            logger.info(f"处理站点: {station_name}")

            # 创建站点输出目录
            station_output_path = os.path.join(qv_result_path, station_name)
            os.makedirs(station_output_path, exist_ok=True)

            # 获取对应的Excel工作表
            sheet_name = f'Sheet{station_count + 1}'

            if sheet_name not in excel_data:
                logger.warning(f"⚠ Excel中未找到工作表: {sheet_name}，跳过该站点")
                station_count += 1
                continue

            allocation_df = excel_data[sheet_name]
            logger.info(f"  工作表 {sheet_name}: {allocation_df.shape[0]}行 × {allocation_df.shape[1]}列")

            # 处理该站点的所有CSV文件
            csv_files = sorted([f for f in os.listdir(station_path) if f.endswith('.csv')])

            for csv_idx, csv_file in enumerate(csv_files):
                csv_path = os.path.join(station_path, csv_file)

                try:
                    # 读取原始CSV
                    original_df = pd.read_csv(csv_path)

                    # ========== 修复：添加列前先检查并删除重复列 ==========
                    # 1. 检查是否已有 allocation_status 列
                    if 'allocation_status' in original_df.columns:
                        logger.debug(f"  {csv_file}: 检测到已存在 allocation_status 列，将覆盖")
                        original_df = original_df.drop(columns=['allocation_status'])

                    # 2. 检查是否有重复列名（通用处理）
                    if original_df.columns.duplicated().any():
                        logger.warning(f"  {csv_file}: 检测到重复列名，进行清理")
                        # 保留第一个，删除后续重复
                        original_df = original_df.loc[:, ~original_df.columns.duplicated()]
                    # ========== 修复结束 ==========

                    # 添加分配状态列
                    if csv_idx < allocation_df.shape[1]:
                        # 从Excel中提取该天线的分配状态
                        allocation_status = allocation_df.iloc[:, csv_idx].values

                        # 确保长度匹配
                        if len(allocation_status) == len(original_df):
                            original_df['allocation_status'] = allocation_status
                        else:
                            logger.warning(
                                f"  ⚠ {csv_file}: 长度不匹配 "
                                f"(CSV={len(original_df)}, Excel={len(allocation_status)})"
                            )
                            # 截断或填充
                            if len(allocation_status) > len(original_df):
                                original_df['allocation_status'] = allocation_status[:len(original_df)]
                            else:
                                padded_status = np.pad(
                                    allocation_status,
                                    (0, len(original_df) - len(allocation_status)),
                                    constant_values='00'
                                )
                                original_df['allocation_status'] = padded_status
                    else:
                        # 如果Excel列数不足，填充默认值
                        original_df['allocation_status'] = '00'

                    # 保存合并后的CSV
                    output_csv_path = os.path.join(station_output_path, csv_file)
                    original_df.to_csv(output_csv_path, index=False, encoding='utf-8')

                    total_files += 1

                except Exception as e:
                    logger.error(f"  ✗ 处理文件失败 {csv_file}: {e}")
                    import traceback
                    logger.error(traceback.format_exc())
                    continue

            logger.info(f"  ✓ 站点 {station_name} 处理完成，生成 {len(csv_files)} 个文件")
            station_count += 1

        # 6. 复制config.ini到结果目录
        config_src = os.path.join(self.dataset_dir, 'config.ini')
        config_dst = os.path.join(result_path, 'config.ini')

        if os.path.exists(config_src):
            shutil.copy2(config_src, config_dst)
            logger.info(f"✓ 配置文件已复制到结果目录")

        # 7. 生成合并摘要
        logger.info("=" * 60)
        logger.info("结果合并完成")
        logger.info(f"  处理站点数: {station_count}")
        logger.info(f"  生成文件数: {total_files}")
        logger.info(f"  输出路径: {result_path}")
        logger.info("=" * 60)

        return result_path


def main():
    """
    独立测试函数
    """
    import sys

    if len(sys.argv) < 4:
        print("用法: python result_combiner.py <dataset_dir> <excel_path> <output_dir>")
        sys.exit(1)

    dataset_dir = sys.argv[1]
    excel_path = sys.argv[2]
    output_dir = sys.argv[3]

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )

    combiner = ResultCombiner(dataset_dir, excel_path, output_dir)
    result_path = combiner.combine()

    print(f"\n✓ 合并完成: {result_path}")


if __name__ == '__main__':
    main()