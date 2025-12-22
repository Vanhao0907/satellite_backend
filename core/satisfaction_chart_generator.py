"""
满足度分析图生成器 - 支持HTML + 图片导出
调用原始脚本生成满足度图，同时导出JPG图片
"""
import os
import sys
import logging
from flask import current_app

logger = logging.getLogger(__name__)


class SatisfactionChartGenerator:
    """满足度分析图生成器 - HTML + 图片版本"""

    def __init__(self, result_dir, output_dir):
        """
        初始化生成器

        Args:
            result_dir: 结果数据目录
            output_dir: 图表输出目录（临时目录）
        """
        self.result_dir = result_dir
        self.output_dir = output_dir

        logger.info(f"满足度图生成器初始化")
        logger.info(f"  结果目录: {result_dir}")
        logger.info(f"  临时输出目录: {output_dir}")

    def generate(self, task_id):
        """
        生成满足度分析图 - HTML + 图片

        Args:
            task_id: 任务ID，用于生成文件名

        Returns:
            tuple: (html_content, image_url)
                - html_content: 满足度图HTML内容
                - image_url: 图片访问URL
        """
        logger.info("=" * 70)
        logger.info("开始生成满足度分析图（HTML + 图片）...")
        logger.info("=" * 70)

        try:
            # ========== 步骤1: 导入原始脚本 ==========
            core_path = os.path.dirname(__file__)
            if core_path not in sys.path:
                sys.path.insert(0, core_path)
                logger.info(f"✓ 添加路径到 sys.path: {core_path}")

            # 导入修改后的原始脚本函数（返回HTML和Figure）
            from satisfaction_original_byhour import generate_satisfaction_chart_with_figure

            logger.info(f"✓ 成功导入 satisfaction_original_byhour 模块")

            # ========== 步骤2: 生成HTML和Figure ==========
            logger.info(f"调用原始满足度图生成函数...")
            html_content, fig = generate_satisfaction_chart_with_figure(
                source_dir=self.result_dir,
                output_dir=self.output_dir
            )

            logger.info(f"✓ HTML生成完成，长度: {len(html_content)} 字符")

            # ========== 步骤3: 导出图片到静态目录 ==========
            image_url = self._export_image(fig, task_id)

            logger.info(f"✓ 满足度图生成完成")
            logger.info(f"  HTML长度: {len(html_content)} 字符")
            logger.info(f"  图片URL: {image_url}")
            logger.info("=" * 70)

            return html_content, image_url

        except ImportError as e:
            logger.error(f"导入失败: {e}")
            raise

        except Exception as e:
            logger.error(f"满足度图生成失败: {e}", exc_info=True)

            # 返回错误提示
            error_html = self._generate_error_html("满足度分析图", str(e))
            return error_html, None

    def _export_image(self, fig, task_id):
        """
        导出Plotly图表为图片并保存到静态目录

        Args:
            fig: Plotly Figure对象
            task_id: 任务ID

        Returns:
            str: 图片访问URL
        """
        try:
            # 获取配置
            static_dir = current_app.config['STATIC_FILES_DIR']
            server_url = current_app.config['SERVER_URL']
            static_prefix = current_app.config['STATIC_URL_PREFIX']

            width = current_app.config['IMAGE_WIDTH']
            height = current_app.config['IMAGE_HEIGHT']
            img_format = current_app.config['IMAGE_FORMAT']

            # 确保静态目录存在
            os.makedirs(static_dir, exist_ok=True)

            # 生成文件名
            filename = f"{task_id}_satisfaction.{img_format}"
            filepath = os.path.join(static_dir, filename)

            logger.info(f"正在导出图片...")
            logger.info(f"  目标路径: {filepath}")
            logger.info(f"  尺寸: {width}x{height}")

            # 使用kaleido导出图片
            fig.write_image(
                filepath,
                format=img_format,
                width=width,
                height=height,
                engine="kaleido"
            )

            # 构建访问URL
            image_url = f"{server_url}{static_prefix}/{filename}"

            logger.info(f"✓ 图片导出成功: {filepath}")
            logger.info(f"✓ 访问URL: {image_url}")

            return image_url

        except Exception as e:
            logger.error(f"图片导出失败: {e}", exc_info=True)
            return None

    def _generate_error_html(self, chart_name, error_message):
        """生成错误提示HTML"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>{chart_name}生成失败</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background-color: #f5f5f5;
                }}
                .error-box {{
                    background-color: white;
                    border-left: 4px solid #dc3545;
                    padding: 20px;
                    margin: 20px auto;
                    max-width: 800px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                h2 {{
                    color: #dc3545;
                    margin-top: 0;
                }}
                .error-message {{
                    color: #6c757d;
                    background-color: #f8f9fa;
                    padding: 10px;
                    border-radius: 4px;
                    font-family: monospace;
                }}
            </style>
        </head>
        <body>
            <div class="error-box">
                <h2>⚠️ {chart_name}生成失败</h2>
                <p><strong>错误信息：</strong></p>
                <div class="error-message">{error_message}</div>
                <p style="margin-top: 20px; color: #6c757d;">
                    请检查日志文件获取详细信息
                </p>
            </div>
        </body>
        </html>
        """