"""
甘特图生成 - 原始脚本封装版（支持返回Figure对象）
基于原始脚本: 6gantetu.py
功能: 将原始脚本封装为可调用的函数，同时返回HTML和Figure对象
"""
import pandas as pd
import plotly.express as px
import os
import glob
import re


def generate_gantt_chart(source_dir, output_dir):
    """
    生成甘特图 - 仅返回HTML（保持向后兼容）

    参数:
    source_dir: 结果CSV文件所在目录
    output_dir: HTML输出目录

    返回:
    str: 甘特图HTML内容
    """
    html_content, _ = generate_gantt_chart_with_figure(source_dir, output_dir)
    return html_content


def generate_gantt_chart_with_figure(source_dir, output_dir):
    """
    生成甘特图 - 返回HTML和Figure对象（新增）

    参数:
    source_dir: 结果CSV文件所在目录
    output_dir: HTML输出目录

    返回:
    tuple: (html_content, fig)
        - html_content: 甘特图HTML字符串
        - fig: Plotly Figure对象
    """
    # ========== 以下代码几乎完全来自原始 6gantetu.py ==========

    # 文件夹路径（参数化）
    folder_path = source_dir

    # 获取文件夹及其子文件夹下所有 CSV 文件的路径
    csv_files = glob.glob(os.path.join(folder_path, '**', '*.csv'), recursive=True)

    # 读取所有 CSV 文件并合并
    df_list = []

    for file in csv_files:
        try:
            # 读取 CSV 文件
            df = pd.read_csv(file)

            # 获取文件所在的父目录名称（QV 或 S）
            parent_dir = os.path.basename(os.path.dirname(os.path.dirname(file)))
            print(parent_dir)

            # 根据父目录名称，为 Sta 字段添加前缀
            if parent_dir in ['QV', 'S']:
                df['sta'] = parent_dir + '_' + df['sta'].astype(str)

            # 将处理后的 DataFrame 添加到列表中
            df_list.append(df)
        except Exception as e:
            print(f"读取文件 {file} 时出错: {e}")

    # 检查是否有数据
    if not df_list:
        print("未找到任何 CSV 文件或所有文件读取失败。")
        # 返回空白图表
        error_html = """
        <!DOCTYPE html>
        <html>
        <head><title>甘特图</title></head>
        <body>
            <h2 style="text-align:center; color:#6C757D;">未找到数据</h2>
            <p style="text-align:center;">未找到任何 CSV 文件或所有文件读取失败</p>
        </body>
        </html>
        """
        return error_html, None

    # 合并所有 DataFrame
    df = pd.concat(df_list, ignore_index=True)
    print("合并后的数据：")
    print(df.head())

    # 转换时间格式
    df['start'] = pd.to_datetime(df['start'], format='mixed')
    df['stop'] = pd.to_datetime(df['stop'], format='mixed')

    # 过滤出 allocation_status 为 1, 2, 3, 4 的数据
    df_filtered = df[df['allocation_status'].isin([1, 2, 3, 4])]

    # 定义 y 轴的排序顺序
    def custom_sort_key(name):
        # 提取前缀和数字部分
        match = re.match(r'([A-Za-z]+)(\d+)', name)
        if match:
            prefix = match.group(1)  # 前缀
            number = int(match.group(2))  # 数字部分
            return (prefix, number)  # 按前缀和数字排序
        return (name, 0)  # 如果没有数字部分，按名称排序

    # 获取 y 轴的排序顺序
    y_order = sorted(df_filtered['sta'].unique(), key=custom_sort_key, reverse=True)

    # 定义试验星的名称列表
    experimental_sats = {'A0001', 'A0002', 'A0004', 'B0001', 'B0002',
                         'B0003', 'B0004', 'B0005', 'B0006', 'B0013'}

    # 定义一个函数来分类星的类型
    def classify_satellite(name):
        if name in experimental_sats:
            return 'CSCN_试验'
        elif name.startswith('A'):
            return 'CSCN_A'
        elif name.startswith('B'):
            return 'CSCN_B'
        elif name.startswith('j'):
            return 'CSCN_j'
        elif name.startswith('q'):
            return 'CSCN_q'
        else:
            return 'CSCN_X'

    # 在 DataFrame 中添加一个新列来存储颜色分类
    df_filtered['Sat_Type'] = df_filtered['sat'].apply(classify_satellite)

    print(df_filtered)

    # 定义颜色映射
    color_map = {
        'CSCN_试验': 'blue',  # 蓝色
        'CSCN_A': '#87CEEB',  # 天蓝色
        'CSCN_X': '#FF6347',  # 番茄红
        'CSCN_j': '#9370DB',  # 中紫色
        'CSCN_q': '#FFA500',  # 橙色
        'CSCN_B': '#98FB98'  # 浅绿色
    }

    # 创建甘特图
    fig = px.timeline(
        df_filtered,
        x_start="start",
        x_end="stop",
        y="sta",
        color="Sat_Type",  # 根据 Sat_Type 列设置颜色
        color_discrete_map=color_map,  # 使用自定义颜色映射
        title="卫星资源分配甘特图 (Satellite Resource Allocation Gantt Chart)",
        labels={"sta": "Antenna", "start": "Start Time", "stop": "End Time"},
    )

    # 调整色块高度
    fig.update_traces(marker=dict(line=dict(width=0)), selector=dict(type='bar'))  # 去掉边框
    fig.update_layout(bargap=0.5)  # 调整色块之间的间距

    # 设置 y 轴排序
    fig.update_yaxes(categoryorder="array", categoryarray=y_order)

    # 设置布局
    fig.update_layout(
        xaxis_title="Time (UTC)",
        yaxis_title="Antenna",
        showlegend=True,  # 显示图例
        legend_title="Satellite Type",  # 图例标题
        height=1000,  # 调整图表高度
    )

    # ========== 修改部分：生成HTML并返回Figure对象 ==========
    # 生成 HTML 内容
    html_content = fig.to_html(
        include_plotlyjs='cdn',
        config={'displayModeBar': True, 'responsive': True}
    )

    # 同时保存文件（保持原有功能）
    os.makedirs(output_dir, exist_ok=True)
    chart_path = os.path.join(output_dir, "gantt_chart.html")
    fig.write_html(chart_path)
    print(f"甘特图已保存: {chart_path}")

    # 返回 HTML 内容和 Figure 对象
    return html_content, fig


def main():
    """
    独立测试函数
    """
    import sys

    if len(sys.argv) < 3:
        print("用法: python gantt_original.py <source_dir> <output_dir>")
        sys.exit(1)

    source_dir = sys.argv[1]
    output_dir = sys.argv[2]

    html_content, fig = generate_gantt_chart_with_figure(source_dir, output_dir)
    print(f"\n✓ 甘特图生成完成")
    print(f"HTML长度: {len(html_content)} 字符")
    print(f"Figure对象: {type(fig)}")


if __name__ == '__main__':
    main()