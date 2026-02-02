# 初始化应用程序
# 调用应用程序工厂并传入参数 config_name 的正确值。
# Flask 开发服务器会自动使用根目录下任何名为 wsgi.py 的文件
# 由于 WSGI 是一种标准规范，使用该文件能确保我们在生产环境中使用的任何 HTTP 服务器（例如 Gunicorn 或 uWSGI）都能立即正常工作。
import os

from application.app import create_app

# 从变量 FLASK_CONFIG 中读取 config_name 的值
app = create_app(os.environ["FLASK_CONFIG"])

# 测试代码：
# FLASK_CONFIG="development" flask run
# 或$env:FLASK_CONFIG="development"; flask run
