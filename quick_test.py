"""
简化版测试脚本 - 学习用
功能：使用写死的测试参数，运行完整后端流程，输出返回给前端的JSON
"""
import requests
import json
import time
from datetime import datetime


# ============================================================
# 写死的测试参数（模拟前端发送的数据）
# ============================================================
TEST_PARAMS = {
    "arc_data": "access_250804",
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


# ============================================================
# 工具函数
# ============================================================
def print_section(title):
    """打印分隔线"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_json_pretty(data, title="JSON数据"):
    """美化打印JSON"""
    print(f"\n{title}:")
    print(json.dumps(data, indent=2, ensure_ascii=False))


def save_json_to_file(data, filename):
    """保存JSON到文件"""
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✓ JSON已保存到: {filename}")


# ============================================================
# 主测试流程
# ============================================================
def main():
    """主测试流程"""

    # 配置
    BASE_URL = "http://localhost:5000"
    API_URL = f"{BASE_URL}/api/simulations"

    print_section("卫星资源调度系统 - 简化版测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"后端地址: {BASE_URL}")

    # ========================================
    # 步骤1: 检查服务器是否启动
    # ========================================
    print_section("步骤1: 检查服务器连接")

    try:
        print("正在连接服务器...")
        response = requests.get(f"{BASE_URL}/health", timeout=5)

        if response.status_code == 200:
            print("✓ 服务器连接成功")
            health_data = response.json()
            print(f"  服务状态: {health_data.get('status')}")
        else:
            print(f"✗ 服务器响应异常: HTTP {response.status_code}")
            return

    except requests.exceptions.ConnectionError:
        print("✗ 无法连接到服务器")
        print("  请先启动后端服务: python app.py")
        return
    except Exception as e:
        print(f"✗ 连接失败: {e}")
        return

    # ========================================
    # 步骤2: 显示请求参数
    # ========================================
    print_section("步骤2: 准备请求参数")

    print_json_pretty(TEST_PARAMS, "请求参数（模拟前端发送）")

    print("\n参数说明:")
    print(f"  数据集: {TEST_PARAMS['arc_data']}")
    print(f"  站点数: {len(TEST_PARAMS['antenna_num'])}")
    print(f"  总天线数: {sum(TEST_PARAMS['antenna_num'].values())}")
    print(f"  时间窗口: {TEST_PARAMS['time_window']}秒")

    # ========================================
    # 步骤3: 发送POST请求
    # ========================================
    print_section("步骤3: 发送POST请求到后端")

    print(f"目标URL: {API_URL}")
    print(f"请求方法: POST")
    print(f"Content-Type: application/json")
    print("\n正在发送请求...")

    # 记录开始时间
    start_time = time.time()

    try:
        response = requests.post(
            API_URL,
            json=TEST_PARAMS,
            headers={'Content-Type': 'application/json'},
            timeout=600  # 10分钟超时
        )

        # 计算耗时
        elapsed_time = time.time() - start_time

        print(f"✓ 收到响应: HTTP {response.status_code}")
        print(f"✓ 请求耗时: {elapsed_time:.2f} 秒")

    except requests.exceptions.Timeout:
        print("✗ 请求超时（超过10分钟）")
        return
    except Exception as e:
        print(f"✗ 请求失败: {e}")
        return

    # ========================================
    # 步骤4: 解析响应
    # ========================================
    print_section("步骤4: 解析后端响应")

    try:
        result = response.json()
        print("✓ 响应格式: JSON")

    except json.JSONDecodeError:
        print("✗ 响应不是有效的JSON格式")
        print(f"原始响应: {response.text[:500]}")
        return

    # ========================================
    # 步骤5: 检查调度是否成功
    # ========================================
    print_section("步骤5: 检查调度结果")

    if response.status_code == 200 and result.get('code') == 200:
        print("✓ 调度执行成功！")
    elif response.status_code == 404:
        print("✗ 数据集不存在")
        print(f"  请检查 data/raw/{TEST_PARAMS['arc_data']}/ 目录")
        print_json_pretty(result, "错误响应")
        return
    elif response.status_code == 400:
        print("✗ 参数错误")
        print_json_pretty(result, "错误响应")
        return
    else:
        print(f"✗ 调度失败: {result.get('message', '未知错误')}")
        print_json_pretty(result, "错误响应")
        return

    # ========================================
    # 步骤6: 显示完整的返回JSON（前端会收到的完整数据）
    # ========================================
    print_section("步骤6: 完整的返回JSON（前端接收）")

    print("=" * 80)
    print("以下是后端返回给前端的完整JSON数据:")
    print("=" * 80)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    print("=" * 80)

    # ========================================
    # 步骤7: 提取并展示关键信息
    # ========================================
    print_section("步骤7: 关键信息提取")

    data = result.get('data', {})

    # 基本信息
    print("\n【基本信息】")
    print(f"  任务ID: {data.get('task_id')}")
    print(f"  执行耗时: {data.get('elapsed_time')} 秒")

    # 调度统计
    statistics = data.get('statistics', {})
    print("\n【调度统计】")
    print(f"  总成功率: {statistics.get('success_rate_all', 0):.2%}")
    print(f"  过滤后成功率: {statistics.get('success_rate_filtered', 0):.2%}")
    print(f"  climb状态成功率: {statistics.get('climb_success_rate', 0):.2%}")
    print(f"  operation状态成功率: {statistics.get('operation_success_rate', 0):.2%}")
    print(f"  总任务数: {statistics.get('total_tasks', 0):,}")
    print(f"  成功任务数: {statistics.get('successful_tasks', 0):,}")
    print(f"  负载标准差: {statistics.get('load_std', 0):.4f}")

    # 数据集统计（新增的功能）
    dataset_stats = data.get('dataset_statistics', {})
    if dataset_stats:
        print("\n【数据集统计】")

        # 站点数据量
        station_data = dataset_stats.get('station_data_count', {})
        if station_data:
            print("\n  站点数据量:")
            for station, count in sorted(station_data.items()):
                print(f"    {station}: {count:,} 条")
            print(f"    总计: {sum(station_data.values()):,} 条")

        # 卫星类型
        satellite_data = dataset_stats.get('satellite_type_count', {})
        if satellite_data:
            print("\n  卫星类型统计:")
            sat_names = {
                'sat_A': 'A类卫星',
                'sat_B': 'B类卫星',
                'sat_j': 'j类卫星',
                'sat_q': 'q类卫星',
                'sat_X': 'X类卫星'
            }
            for sat_key, count in satellite_data.items():
                sat_name = sat_names.get(sat_key, sat_key)
                print(f"    {sat_name}: {count:,} 个唯一任务")
            print(f"    总计: {sum(satellite_data.values()):,} 个唯一任务")

    # 验证结果
    validation = data.get('validation', {})
    print("\n【验证结果】")
    print(f"  无溢出: {validation.get('no_overflow', False)}")
    print(f"  无重叠: {validation.get('no_overlap', False)}")
    print(f"  消息: {validation.get('message', 'N/A')}")

    # 图表信息
    charts = data.get('charts', {})
    if charts:
        print("\n【图表生成】")
        gantt_html_len = len(charts.get('gantt_chart_html', ''))
        gantt_url = charts.get('gantt_chart_image_url', 'N/A')
        satisfaction_html_len = len(charts.get('satisfaction_chart_html', ''))
        satisfaction_url = charts.get('satisfaction_chart_image_url', 'N/A')

        print(f"  甘特图HTML: {gantt_html_len:,} 字符")
        print(f"  甘特图图片URL: {gantt_url}")
        print(f"  满足度图HTML: {satisfaction_html_len:,} 字符")
        print(f"  满足度图图片URL: {satisfaction_url}")

    # ========================================
    # 步骤8: 保存结果到文件
    # ========================================
    print_section("步骤8: 保存结果到文件")

    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # 保存完整JSON
    full_json_file = f"test_result_{timestamp}_full.json"
    save_json_to_file(result, full_json_file)

    # 保存数据集统计
    if dataset_stats:
        stats_file = f"test_result_{timestamp}_dataset_stats.json"
        save_json_to_file(dataset_stats, stats_file)

    # 保存甘特图HTML
    if charts.get('gantt_chart_html'):
        gantt_file = f"test_result_{timestamp}_gantt.html"
        with open(gantt_file, 'w', encoding='utf-8') as f:
            f.write(charts['gantt_chart_html'])
        print(f"✓ 甘特图HTML已保存到: {gantt_file}")

    # 保存满足度图HTML
    if charts.get('satisfaction_chart_html'):
        satisfaction_file = f"test_result_{timestamp}_satisfaction.html"
        with open(satisfaction_file, 'w', encoding='utf-8') as f:
            f.write(charts['satisfaction_chart_html'])
        print(f"✓ 满足度图HTML已保存到: {satisfaction_file}")

    # ========================================
    # 完成
    # ========================================
    print_section("测试完成")
    print("🎉 所有步骤执行成功！")
    print(f"\n生成的文件:")
    print(f"  1. {full_json_file} - 完整JSON响应")
    if dataset_stats:
        print(f"  2. {stats_file} - 数据集统计")
    if charts.get('gantt_chart_html'):
        print(f"  3. {gantt_file} - 甘特图HTML")
    if charts.get('satisfaction_chart_html'):
        print(f"  4. {satisfaction_file} - 满足度图HTML")
    print("\n" + "=" * 80)


# ============================================================
# 程序入口
# ============================================================
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ 用户中断测试")
    except Exception as e:
        print(f"\n\n✗ 程序异常: {e}")
        import traceback
        traceback.print_exc()