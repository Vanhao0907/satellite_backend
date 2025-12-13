"""
卫星资源调度API测试脚本
功能：测试后端API接口是否正常工作
"""
import requests
import json
import time
import sys
from datetime import datetime


class SchedulingAPITester:
    """API测试类"""

    def __init__(self, base_url="http://localhost:5000"):
        """
        初始化测试器

        Args:
            base_url: API基础URL
        """
        self.base_url = base_url
        self.test_results = []

    def print_header(self, title):
        """打印测试标题"""
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)

    def print_success(self, message):
        """打印成功信息"""
        print(f"✅ {message}")

    def print_error(self, message):
        """打印错误信息"""
        print(f"❌ {message}")

    def print_info(self, message):
        """打印提示信息"""
        print(f"ℹ️  {message}")

    def record_test(self, test_name, passed, message=""):
        """记录测试结果"""
        self.test_results.append({
            'test': test_name,
            'passed': passed,
            'message': message
        })

    def test_server_connection(self):
        """测试1: 服务器连接"""
        self.print_header("测试1: 服务器连接")

        try:
            response = requests.get(f"{self.base_url}/health", timeout=5)

            if response.status_code == 200:
                self.print_success(f"服务器连接成功: {self.base_url}")
                data = response.json()
                self.print_info(f"服务状态: {data.get('status', 'unknown')}")
                self.record_test("服务器连接", True)
                return True
            else:
                self.print_error(f"服务器响应异常: HTTP {response.status_code}")
                self.record_test("服务器连接", False, f"HTTP {response.status_code}")
                return False

        except requests.exceptions.ConnectionError:
            self.print_error("无法连接到服务器，请确保服务已启动")
            self.print_info("提示: 运行 python app.py 启动服务")
            self.record_test("服务器连接", False, "连接失败")
            return False
        except Exception as e:
            self.print_error(f"连接测试失败: {str(e)}")
            self.record_test("服务器连接", False, str(e))
            return False

    def test_api_endpoint(self):
        """测试2: API端点测试"""
        self.print_header("测试2: API端点测试")

        try:
            response = requests.get(f"{self.base_url}/api/simulations/test", timeout=5)

            if response.status_code == 200:
                data = response.json()
                self.print_success("API端点正常")
                self.print_info(f"端点: {data.get('data', {}).get('endpoint', 'N/A')}")
                self.print_info(f"版本: {data.get('data', {}).get('version', 'N/A')}")
                self.record_test("API端点", True)
                return True
            else:
                self.print_error(f"API端点响应异常: HTTP {response.status_code}")
                self.record_test("API端点", False, f"HTTP {response.status_code}")
                return False

        except Exception as e:
            self.print_error(f"API端点测试失败: {str(e)}")
            self.record_test("API端点", False, str(e))
            return False

    def load_test_data(self, filename="test_request.json"):
        """加载测试数据"""
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            self.print_error(f"测试数据文件不存在: {filename}")
            return None
        except json.JSONDecodeError as e:
            self.print_error(f"测试数据JSON格式错误: {str(e)}")
            return None

    def test_parameter_validation(self):
        """测试3: 参数验证"""
        self.print_header("测试3: 参数验证")

        # 测试3.1: 缺少参数
        print("\n[3.1] 测试缺少必需参数...")

        test_cases = [
            ({"antenna_num": {"CM": 6}, "time_window": 300}, "缺少arc_data"),
            ({"arc_data": "test", "time_window": 300}, "缺少antenna_num"),
            ({"arc_data": "test", "antenna_num": {"CM": 6}}, "缺少time_window"),
        ]

        all_passed = True
        for data, desc in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/simulations",
                    json=data,
                    timeout=5
                )

                if response.status_code == 400:
                    self.print_success(f"{desc} → 正确返回400错误")
                else:
                    self.print_error(f"{desc} → 应返回400，实际返回{response.status_code}")
                    all_passed = False
            except Exception as e:
                self.print_error(f"{desc} → 测试失败: {str(e)}")
                all_passed = False

        # 测试3.2: 错误的参数类型
        print("\n[3.2] 测试错误的参数类型...")

        test_cases = [
            ({"arc_data": 123, "antenna_num": {"CM": 6}, "time_window": 300}, "arc_data非字符串"),
            ({"arc_data": "test", "antenna_num": "wrong", "time_window": 300}, "antenna_num非对象"),
            ({"arc_data": "test", "antenna_num": {"CM": 6}, "time_window": "300"}, "time_window非数字"),
        ]

        for data, desc in test_cases:
            try:
                response = requests.post(
                    f"{self.base_url}/api/simulations",
                    json=data,
                    timeout=5
                )

                if response.status_code == 400:
                    self.print_success(f"{desc} → 正确返回400错误")
                else:
                    self.print_error(f"{desc} → 应返回400，实际返回{response.status_code}")
                    all_passed = False
            except Exception as e:
                self.print_error(f"{desc} → 测试失败: {str(e)}")
                all_passed = False

        self.record_test("参数验证", all_passed)
        return all_passed

    def test_scheduling_execution(self, test_data):
        """测试4: 调度执行（核心功能）"""
        self.print_header("测试4: 调度执行（核心功能）")

        if not test_data:
            self.print_error("没有可用的测试数据")
            self.record_test("调度执行", False, "无测试数据")
            return False

        # 显示测试数据
        print("\n[请求数据]")
        print(json.dumps(test_data, indent=2, ensure_ascii=False))

        print("\n[发送请求...]")
        start_time = time.time()

        try:
            response = requests.post(
                f"{self.base_url}/api/simulations",
                json=test_data,
                timeout=600  # 10分钟超时
            )

            elapsed_time = time.time() - start_time

            print(f"\n[响应状态] HTTP {response.status_code}")
            print(f"[耗时] {elapsed_time:.2f}秒")

            if response.status_code == 200:
                result = response.json()

                # 验证响应结构
                if result.get('code') == 200:
                    data = result.get('data', {})

                    self.print_success("调度执行成功！")
                    print("\n[返回数据]")
                    print(f"  任务ID: {data.get('task_id', 'N/A')}")
                    print(f"  执行耗时: {data.get('elapsed_time', 'N/A')}秒")

                    # 统计信息
                    stats = data.get('statistics', {})
                    if stats:
                        print(f"\n[统计信息]")
                        print(f"  总成功率: {stats.get('success_rate_all', 0):.2%}")
                        print(f"  过滤后成功率: {stats.get('success_rate_filtered', 0):.2%}")
                        print(f"  climb状态成功率: {stats.get('climb_success_rate', 0):.2%}")
                        print(f"  operation状态成功率: {stats.get('operation_success_rate', 0):.2%}")
                        print(f"  负载标准差: {stats.get('load_std', 0):.4f}")

                    # 图表信息
                    charts = data.get('charts', {})
                    if charts:
                        print(f"\n[图表生成]")
                        gantt_size = len(charts.get('gantt_chart_html', ''))
                        satisfaction_size = len(charts.get('satisfaction_chart_html', ''))
                        print(f"  甘特图: {gantt_size} 字符")
                        print(f"  满足度图表: {satisfaction_size} 字符")

                    # 验证信息
                    validation = data.get('validation', {})
                    if validation:
                        print(f"\n[验证结果]")
                        print(f"  无溢出: {validation.get('no_overflow', False)}")
                        print(f"  无重叠: {validation.get('no_overlap', False)}")
                        print(f"  消息: {validation.get('message', 'N/A')}")

                    self.record_test("调度执行", True)
                    return True
                else:
                    self.print_error(f"API返回错误: {result.get('message', 'Unknown error')}")
                    self.record_test("调度执行", False, result.get('message', ''))
                    return False

            elif response.status_code == 404:
                self.print_error("数据集不存在")
                self.print_info(f"请检查 data/raw/{test_data['arc_data']}/ 目录是否存在")
                self.record_test("调度执行", False, "数据集不存在")
                return False

            else:
                error_data = response.json()
                self.print_error(f"调度失败: {error_data.get('message', 'Unknown error')}")
                self.record_test("调度执行", False, error_data.get('message', ''))
                return False

        except requests.exceptions.Timeout:
            self.print_error("请求超时（超过10分钟）")
            self.record_test("调度执行", False, "超时")
            return False
        except Exception as e:
            self.print_error(f"调度执行失败: {str(e)}")
            self.record_test("调度执行", False, str(e))
            return False

    def run_all_tests(self, test_data_file="test_request.json"):
        """运行所有测试"""
        print("\n" + "=" * 70)
        print("  卫星资源调度API测试")
        print("  测试时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        print("=" * 70)

        # 测试1: 服务器连接
        if not self.test_server_connection():
            self.print_summary()
            return False

        # 测试2: API端点
        self.test_api_endpoint()

        # 测试3: 参数验证
        self.test_parameter_validation()

        # 测试4: 调度执行
        self.print_header("加载测试数据")
        test_data = self.load_test_data(test_data_file)
        if test_data:
            self.print_success(f"成功加载测试数据: {test_data_file}")
            self.test_scheduling_execution(test_data)
        else:
            self.print_error("无法加载测试数据，跳过调度执行测试")
            self.record_test("调度执行", False, "无测试数据")

        # 打印测试摘要
        self.print_summary()

        # 返回总体结果
        return all(result['passed'] for result in self.test_results)

    def print_summary(self):
        """打印测试摘要"""
        self.print_header("测试摘要")

        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r['passed'])
        failed = total - passed

        print(f"\n总计: {total} 个测试")
        print(f"通过: {passed} 个 ✅")
        print(f"失败: {failed} 个 ❌")
        print(f"成功率: {(passed / total * 100) if total > 0 else 0:.1f}%")

        if failed > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  ❌ {result['test']}: {result['message']}")

        print("\n" + "=" * 70)

        if passed == total:
            print("🎉 所有测试通过！API工作正常！")
        else:
            print("⚠️  部分测试失败，请检查上述错误信息")

        print("=" * 70 + "\n")


def main():
    """主函数"""
    # 解析命令行参数
    base_url = "http://localhost:5000"
    test_file = "test_request.json"

    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    if len(sys.argv) > 2:
        test_file = sys.argv[2]

    # 创建测试器
    tester = SchedulingAPITester(base_url)

    # 运行所有测试
    success = tester.run_all_tests(test_file)

    # 返回退出码
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()