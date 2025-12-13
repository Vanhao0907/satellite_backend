@echo off
REM 快速部署脚本 - Windows版本

echo ==========================================
echo 卫星调度算法 - 快速部署脚本 (Windows)
echo ==========================================
echo.

REM 检查是否在正确的目录
if not exist "app.py" (
    echo 错误: 请在项目根目录 satellite-scheduling-backend\ 运行此脚本
    pause
    exit /b 1
)

echo 步骤1: 创建算法模块目录...
if not exist "core\scheduling" mkdir core\scheduling
echo. > core\scheduling\__init__.py
echo ✓ 目录创建完成
echo.

echo 步骤2: 检查需要复制的文件...
echo 请将以下文件放到当前目录的 legacy\ 文件夹中：
echo   - algorithm.py
echo   - simulated_annealing.py
echo   - data_processing.py
echo   - validate_results.py
echo   - antenna_load_balance.py
echo   - utils.py
echo.

if not exist "legacy" (
    echo 正在创建 legacy\ 目录...
    mkdir legacy
    echo ✓ legacy\ 目录已创建
    echo.
    echo 请将上述6个文件复制到 legacy\ 目录，然后重新运行此脚本
    pause
    exit /b 0
)

echo 步骤3: 复制算法模块文件...

set "missing=0"

if exist "legacy\algorithm.py" (
    copy "legacy\algorithm.py" "core\scheduling\algorithm.py" >nul
    echo   ✓ 复制: algorithm.py
) else (
    echo   ✗ 缺失: algorithm.py
    set "missing=1"
)

if exist "legacy\simulated_annealing.py" (
    copy "legacy\simulated_annealing.py" "core\scheduling\simulated_annealing.py" >nul
    echo   ✓ 复制: simulated_annealing.py
) else (
    echo   ✗ 缺失: simulated_annealing.py
    set "missing=1"
)

if exist "legacy\data_processing.py" (
    copy "legacy\data_processing.py" "core\scheduling\data_processing.py" >nul
    echo   ✓ 复制: data_processing.py
) else (
    echo   ✗ 缺失: data_processing.py
    set "missing=1"
)

if exist "legacy\validate_results.py" (
    copy "legacy\validate_results.py" "core\scheduling\validate_results.py" >nul
    echo   ✓ 复制: validate_results.py
) else (
    echo   ✗ 缺失: validate_results.py
    set "missing=1"
)

if exist "legacy\antenna_load_balance.py" (
    copy "legacy\antenna_load_balance.py" "core\scheduling\antenna_load_balance.py" >nul
    echo   ✓ 复制: antenna_load_balance.py
) else (
    echo   ✗ 缺失: antenna_load_balance.py
    set "missing=1"
)

if exist "legacy\utils.py" (
    copy "legacy\utils.py" "core\scheduling\utils.py" >nul
    echo   ✓ 复制: utils.py
) else (
    echo   ✗ 缺失: utils.py
    set "missing=1"
)

echo.

if "%missing%"=="1" (
    echo 警告: 某些文件缺失，请补充后重新运行
    pause
    exit /b 1
)

echo 步骤4: 替换调度算法主文件...
if exist "core\scheduling_algorithm_complete.py" (
    copy "core\scheduling_algorithm_complete.py" "core\scheduling_algorithm.py" >nul
    echo   ✓ scheduling_algorithm.py 已更新
) else (
    echo   ⚠ 未找到 scheduling_algorithm_complete.py，跳过
)

echo.
echo ==========================================
echo 部署完成！
echo ==========================================
echo.
echo 下一步操作：
echo 1. 测试服务: python app.py
echo 2. 检查健康: curl http://localhost:5000/health
echo 3. 测试接口: curl -X POST http://localhost:5000/api/simulations ^
echo               -H "Content-Type: application/json" ^
echo               -d @test_request.json
echo.
pause
