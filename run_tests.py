#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
自动化测试脚本 - 卫星调度系统完整性检查
运行此脚本可自动检查项目完整性和连通性
"""
import sys
import os
import subprocess
import json
from pathlib import Path

# 颜色代码
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'


class ProjectTester:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.warnings = 0

    def print_header(self, text):
        print(f"\n{BLUE}{'=' * 70}{RESET}")
        print(f"{BLUE}{text:^70}{RESET}")
        print(f"{BLUE}{'=' * 70}{RESET}\n")

    def print_success(self, text):
        print(f"{GREEN}✓{RESET} {text}")
        self.passed += 1

    def print_failure(self, text):
        print(f"{RED}✗{RESET} {text}")
        self.failed += 1

    def print_warning(self, text):
        print(f"{YELLOW}⚠{RESET} {text}")
        self.warnings += 1

    def print_info(self, text):
        print(f"  {text}")

    def test_python_version(self):
        """测试Python版本"""
        self.print_header("测试 1: Python环境检查")

        version = sys.version_info
        if version.major >= 3 and version.minor >= 8:
            self.print_success(f"Python版本: {version.major}.{version.minor}.{version.micro}")
        else:
            self.print_failure(f"Python版本过低: {version.major}.{version.minor} (需要 >= 3.8)")

    def test_dependencies(self):
        """测试依赖包"""
        self.print_header("测试 2: 依赖包检查")

        required_packages = [
            'flask',
            'flask_cors',
            'pandas',
            'numpy',
            'openpyxl',
            'plotly'
            #'python-dotenv'
        ]

        for package in required_packages:
            try:
                __import__(package.replace('-', '_'))
                self.print_success(f"{package} 已安装")
            except ImportError:
                self.print_failure(f"{package} 未安装")

    def test_project_structure(self):
        """测试项目结构"""
        self.print_header("测试 3: 项目结构检查")

        required_files = [
            'app.py',
            'config.py',
            '.env',
            'requirements.txt',
            'test_request.json',
        ]

        required_dirs = [
            'api',
            'core',
            'services',
            'data/raw',
            'data/temp',
            'logs'
        ]

        for file in required_files:
            if os.path.exists(file):
                self.print_success(f"文件存在: {file}")
            else:
                self.print_failure(f"文件缺失: {file}")

        for dir in required_dirs:
            if os.path.exists(dir):
                self.print_success(f"目录存在: {dir}/")
            else:
                self.print_warning(f"目录缺失: {dir}/ (将自动创建)")
                os.makedirs(dir, exist_ok=True)

    def test_module_imports(self):
        """测试模块导入"""
        self.print_header("测试 4: 模块导入检查")

        test_imports = [
            ('config', 'get_config'),
            ('api.simulation_api', 'simulation_bp'),
            ('services.scheduling_service', 'SchedulingService'),
            ('core.dataset_builder', 'DatasetBuilder'),
            ('core.result_combiner', 'ResultCombiner'),
            ('core.gantt_chart_generator', 'GanttChartGenerator'),
            ('core.satisfaction_chart_generator', 'SatisfactionChartGenerator'),
        ]

        for module_name, obj_name in test_imports:
            try:
                module = __import__(module_name, fromlist=[obj_name])
                getattr(module, obj_name)
                self.print_success(f"导入成功: {module_name}.{obj_name}")
            except Exception as e:
                self.print_failure(f"导入失败: {module_name}.{obj_name} - {str(e)}")

    def test_algorithm_modules(self):
        """测试调度算法模块"""
        self.print_header("测试 5: 调度算法模块检查")

        algorithm_files = [
            'core/scheduling/__init__.py',
            'core/scheduling/algorithm.py',
            'core/scheduling/simulated_annealing.py',
            'core/scheduling/data_processing.py',
            'core/scheduling/validate_results.py',
            'core/scheduling/antenna_load_balance.py',
            'core/scheduling/utils.py',
        ]

        all_exist = True
        for file in algorithm_files:
            if os.path.exists(file):
                self.print_success(f"算法模块存在: {file}")
            else:
                self.print_failure(f"算法模块缺失: {file}")
                all_exist = False

        if not all_exist:
            self.print_warning("请运行 deploy.sh 或 deploy.bat 来复制算法模块文件")

    def test_config_file(self):
        """测试配置文件"""
        self.print_header("测试 6: 配置文件检查")

        try:
            from config import get_config
            config = get_config()
            self.print_success("配置加载成功")

            # 检查关键配置
            self.print_info(f"  环境: {config.ENV}")
            self.print_info(f"  端口: {config.PORT}")
            self.print_info(f"  原始数据目录: {config.RAW_DATA_DIR}")
            self.print_info(f"  临时数据目录: {config.TEMP_DATA_DIR}")

        except Exception as e:
            self.print_failure(f"配置加载失败: {e}")

    def test_test_data(self):
        """测试测试数据"""
        self.print_header("测试 7: 测试数据检查")

        # 检查test_request.json
        if os.path.exists('test_request.json'):
            try:
                with open('test_request.json', 'r', encoding='utf-8') as f:
                    data = json.load(f)

                self.print_success("test_request.json 格式正确")

                # 检查必需字段
                required_fields = ['arc_data', 'antenna_num', 'strategy', 'time_window']
                for field in required_fields:
                    if field in data:
                        self.print_success(f"  包含必需字段: {field}")
                    else:
                        self.print_failure(f"  缺少必需字段: {field}")

            except Exception as e:
                self.print_failure(f"test_request.json 格式错误: {e}")
        else:
            self.print_failure("test_request.json 不存在")

        # 检查原始Excel数据
        if os.path.exists('data/raw'):
            subdirs = [d for d in os.listdir('data/raw') if os.path.isdir(os.path.join('data/raw', d))]
            if subdirs:
                self.print_success(f"找到 {len(subdirs)} 个数据集目录")
                for subdir in subdirs:
                    self.print_info(f"  - {subdir}")
            else:
                self.print_warning("data/raw/ 目录为空，请放置Excel数据文件")
        else:
            self.print_warning("data/raw/ 目录不存在")

    def test_app_startup(self):
        """测试应用启动（不实际启动）"""
        self.print_header("测试 8: 应用启动检查")

        try:
            # 只导入，不实际运行
            from app import create_app
            app = create_app('testing')
            self.print_success("Flask应用创建成功")

            # 检查蓝图
            if 'simulation' in app.blueprints:
                self.print_success("API蓝图注册成功")
            else:
                self.print_failure("API蓝图未注册")

        except Exception as e:
            self.print_failure(f"应用创建失败: {e}")

    def print_summary(self):
        """打印测试摘要"""
        self.print_header("测试摘要")

        total = self.passed + self.failed
        pass_rate = (self.passed / total * 100) if total > 0 else 0

        print(f"总测试数: {total}")
        print(f"{GREEN}通过: {self.passed}{RESET}")
        print(f"{RED}失败: {self.failed}{RESET}")
        print(f"{YELLOW}警告: {self.warnings}{RESET}")
        print(f"通过率: {pass_rate:.1f}%\n")

        if self.failed == 0:
            print(f"{GREEN}{'=' * 70}{RESET}")
            print(f"{GREEN}{'✓ 所有测试通过！项目可以运行':^70}{RESET}")
            print(f"{GREEN}{'=' * 70}{RESET}\n")
            print("下一步操作:")
            print("1. 启动服务: python app.py")
            print(
                "2. 测试接口: curl -X POST http://localhost:5000/api/simulations -H 'Content-Type: application/json' -d @test_request.json")
        else:
            print(f"{RED}{'=' * 70}{RESET}")
            print(f"{RED}{'✗ 存在失败项，请检查上述输出':^70}{RESET}")
            print(f"{RED}{'=' * 70}{RESET}\n")

            if self.failed > 0:
                print("建议操作:")
                print("1. 检查依赖安装: pip install -r requirements.txt")
                print("2. 检查算法模块: 运行 deploy.sh 或 deploy.bat")
                print("3. 准备测试数据: 放置Excel文件到 data/raw/")

        return self.failed == 0

    def run_all_tests(self):
        """运行所有测试"""
        print(f"\n{BLUE}{'*' * 70}{RESET}")
        print(f"{BLUE}{'卫星调度系统 - 自动化完整性测试':^70}{RESET}")
        print(f"{BLUE}{'*' * 70}{RESET}")

        self.test_python_version()
        self.test_dependencies()
        self.test_project_structure()
        self.test_module_imports()
        self.test_algorithm_modules()
        self.test_config_file()
        self.test_test_data()
        self.test_app_startup()

        return self.print_summary()


if __name__ == '__main__':
    tester = ProjectTester()
    success = tester.run_all_tests()

    # 退出码：0表示成功，1表示失败
    sys.exit(0 if success else 1)