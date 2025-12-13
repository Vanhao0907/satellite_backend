"""
快速测试脚本 - 简化版
只测试核心功能：从test_request.json读取参数并调用API
"""
import requests
import json
import sys


def test_scheduling_api():
    """测试调度API"""

    # 配置
    API_URL = "http://localhost:5000/api/simulations"
    TEST_FILE = "test_request.json"

    print("=" * 60)
    print("卫星资源调度API快速测试")
    print("=" * 60)

    # 1. 读取测试数据
    print("\n[1] 读取测试数据...")
    try:
        with open(TEST_FILE, 'r', encoding='utf-8') as f:
            test_data = json.load(f)
        print(f"✅ 成功读取 {TEST_FILE}")
        print("\n请求参数:")
        print(json.dumps(test_data, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"❌ 读取测试数据失败: {e}")
        return False

    # 2. 发送请求
    print("\n" + "=" * 60)
    print("[2] 发送请求到后端...")
    print(f"URL: {API_URL}")

    try:
        response = requests.post(
            API_URL,
            json=test_data,
            headers={'Content-Type': 'application/json'},
            timeout=600  # 10分钟超时
        )

        print(f"响应状态码: {response.status_code}")

    except requests.exceptions.ConnectionError:
        print("❌ 连接失败！请确保后端服务已启动")
        print("提示: 运行 python app.py 启动服务")
        return False
    except requests.exceptions.Timeout:
        print("❌ 请求超时（超过10分钟）")
        return False
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return False

    # 3. 解析响应
    print("\n" + "=" * 60)
    print("[3] 解析响应...")

    try:
        result = response.json()

        if response.status_code == 200 and result.get('code') == 200:
            print("✅ 调度成功！\n")

            data = result.get('data', {})

            # 基本信息
            print("=" * 60)
            print("返回结果:")
            print("=" * 60)
            print(f"任务ID: {data.get('task_id')}")
            print(f"执行耗时: {data.get('elapsed_time')}秒")

            # 统计信息
            stats = data.get('statistics', {})
            print(f"\n统计信息:")
            print(f"  总成功率: {stats.get('success_rate_all', 0):.2%}")
            print(f"  过滤后成功率: {stats.get('success_rate_filtered', 0):.2%}")
            print(f"  负载标准差: {stats.get('load_std', 0):.4f}")

            # 图表信息
            charts = data.get('charts', {})
            print(f"\n图表生成:")
            print(f"  甘特图HTML: {len(charts.get('gantt_chart_html', ''))} 字符")
            print(f"  满足度图表HTML: {len(charts.get('satisfaction_chart_html', ''))} 字符")

            # 验证
            validation = data.get('validation', {})
            print(f"\n验证结果:")
            print(f"  无溢出: {validation.get('no_overflow')}")
            print(f"  无重叠: {validation.get('no_overlap')}")
            print(f"  消息: {validation.get('message')}")

            print("\n" + "=" * 60)
            print("🎉 测试通过！")
            print("=" * 60)
            return True

        elif response.status_code == 404:
            print(f"❌ 数据集不存在: {test_data['arc_data']}")
            print(f"请检查 data/raw/{test_data['arc_data']}/QV/ 目录")
            return False

        elif response.status_code == 400:
            print(f"❌ 参数错误: {result.get('message')}")
            return False

        else:
            print(f"❌ 调度失败: {result.get('message')}")
            return False

    except json.JSONDecodeError:
        print(f"❌ 响应不是有效的JSON")
        print(f"原始响应: {response.text[:500]}")
        return False
    except Exception as e:
        print(f"❌ 解析响应失败: {e}")
        return False


if __name__ == "__main__":
    success = test_scheduling_api()
    sys.exit(0 if success else 1)