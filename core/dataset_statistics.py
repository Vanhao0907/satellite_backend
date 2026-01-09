"""
数据集统计模块
功能：统计数据集中的站点数据量和卫星类型数量（去重）
"""
import os
import pandas as pd
import logging

logger = logging.getLogger(__name__)


class DatasetStatistics:
    """
    数据集统计器
    统计站点数据量和卫星类型数量
    """

    def __init__(self, dataset_dir, antenna_config):
        """
        初始化统计器

        Args:
            dataset_dir: 数据集目录路径（包含QV子目录）
            antenna_config: 天线配置字典 {"CM": 6, "JMS": 14, ...}
        """
        self.dataset_dir = dataset_dir
        self.antenna_config = antenna_config
        self.qv_dir = os.path.join(dataset_dir, 'QV')

        logger.info(f"数据集统计器初始化")
        logger.info(f"  数据集目录: {dataset_dir}")
        logger.info(f"  QV目录: {self.qv_dir}")

    def calculate(self):
        """
        执行统计计算

        Returns:
            dict: {
                "station_data_counts": {"CM": 1200, "JMS": 2800, ...},
                "satellite_type_counts": {"A": 150, "B": 200, ...},
                "total_unique_tasks": 450
            }
        """
        logger.info("开始统计数据集信息...")

        # 统计站点数据量
        station_counts = self._calculate_station_counts()

        # 统计卫星类型（去重）
        satellite_counts, total_unique = self._calculate_satellite_types()

        result = {
            'station_data_counts': station_counts,
            'satellite_type_counts': satellite_counts,
            'total_unique_tasks': total_unique
        }

        logger.info("数据集统计完成")
        logger.info(f"  站点数据量: {station_counts}")
        logger.info(f"  卫星类型统计: {satellite_counts}")
        logger.info(f"  总任务数（去重）: {total_unique}")

        return result

    def _calculate_station_counts(self):
        """
        统计各站点数据量

        逻辑：读取每个站点第一个天线的CSV文件行数 × 天线数量

        Returns:
            dict: {"CM": 1200, "JMS": 2800, ...}
        """
        logger.info("统计站点数据量...")
        station_counts = {}

        for station, antenna_count in self.antenna_config.items():
            station_dir = os.path.join(self.qv_dir, station)

            if not os.path.exists(station_dir):
                logger.warning(f"  ⚠ 站点目录不存在: {station}")
                station_counts[station] = 0
                continue

            # 找到第一个CSV文件
            csv_files = sorted([f for f in os.listdir(station_dir) if f.endswith('.csv')])

            if not csv_files:
                logger.warning(f"  ⚠ 站点 {station} 没有CSV文件")
                station_counts[station] = 0
                continue

            # 读取第一个CSV文件的行数
            first_csv_path = os.path.join(station_dir, csv_files[0])

            try:
                df = pd.read_csv(first_csv_path)
                single_antenna_count = len(df)

                # 总数据量 = 单个天线数据量 × 天线数量
                total_count = single_antenna_count * antenna_count

                station_counts[station] = total_count

                logger.info(f"  {station}: 单天线={single_antenna_count}行, "
                           f"天线数={antenna_count}, 总计={total_count}行")

            except Exception as e:
                logger.error(f"  ✗ 读取 {station} 数据失败: {e}")
                station_counts[station] = 0

        return station_counts

    def _calculate_satellite_types(self):
        """
        统计卫星类型数量（去重）

        逻辑：
        1. 遍历所有站点的所有CSV文件
        2. 提取 (sat, laps, status) 组合
        3. 使用set去重
        4. 按卫星名称首字母分类统计

        Returns:
            tuple: (satellite_counts, total_unique)
                - satellite_counts: {"A": 150, "B": 200, ...}
                - total_unique: 总任务数（去重后）
        """
        logger.info("统计卫星类型（去重）...")

        # 用于存储所有唯一的 (sat, laps, status) 组合
        unique_tasks = set()

        # 遍历所有站点
        for station in self.antenna_config.keys():
            station_dir = os.path.join(self.qv_dir, station)

            if not os.path.exists(station_dir):
                continue

            # 遍历该站点的所有CSV文件
            csv_files = [f for f in os.listdir(station_dir) if f.endswith('.csv')]

            for csv_file in csv_files:
                csv_path = os.path.join(station_dir, csv_file)

                try:
                    df = pd.read_csv(csv_path)

                    # 提取需要的列（兼容不同的列名格式）
                    sat_col = 'sat' if 'sat' in df.columns else 'Sat'
                    laps_col = 'laps' if 'laps' in df.columns else 'Laps'
                    status_col = 'Status' if 'Status' in df.columns else 'status'

                    # 检查列是否存在
                    if sat_col not in df.columns:
                        logger.warning(f"  ⚠ {csv_file} 缺少 'sat' 列")
                        continue
                    if laps_col not in df.columns:
                        logger.warning(f"  ⚠ {csv_file} 缺少 'laps' 列")
                        continue
                    if status_col not in df.columns:
                        logger.warning(f"  ⚠ {csv_file} 缺少 'status' 列")
                        continue

                    # 提取 (sat, laps, status) 组合并添加到集合
                    for _, row in df.iterrows():
                        sat = str(row[sat_col])
                        laps = int(row[laps_col])
                        status = str(row[status_col])
                        unique_tasks.add((sat, laps, status))

                except Exception as e:
                    logger.error(f"  ✗ 读取 {csv_file} 失败: {e}")
                    continue

        logger.info(f"  总任务数（去重）: {len(unique_tasks)}")

        # 按卫星类型分类统计
        satellite_counts = {
            'A': 0,
            'B': 0,
            'j': 0,
            'q': 0,
            'X': 0
        }

        for sat, _, _ in unique_tasks:
            first_char = sat[0] if sat else ''

            if first_char in satellite_counts:
                satellite_counts[first_char] += 1

        logger.info(f"  卫星类型统计（去重）: {satellite_counts}")

        return satellite_counts, len(unique_tasks)


def main():
    """
    独立测试函数
    """
    import sys

    if len(sys.argv) < 2:
        print("用法: python dataset_statistics.py <dataset_dir>")
        print("示例: python dataset_statistics.py data/temp/task_xxx/dataset/access_251212_pro")
        sys.exit(1)

    dataset_dir = sys.argv[1]

    # 示例天线配置
    antenna_config = {
        'CM': 6,
        'JMS': 14,
        'KEL': 18,
        'KS': 5,
        'MH': 3,
        'TC': 10,
        'WC': 6,
        'XA': 8
    }

    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] %(levelname)s: %(message)s'
    )

    stats = DatasetStatistics(dataset_dir, antenna_config)
    result = stats.calculate()

    print("\n统计结果:")
    print(f"站点数据量: {result['station_data_counts']}")
    print(f"卫星类型统计: {result['satellite_type_counts']}")
    print(f"总任务数: {result['total_unique_tasks']}")


if __name__ == '__main__':
    main()