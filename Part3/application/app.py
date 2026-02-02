from flask import Flask
from application.models import User


# 创建一个应用程序工厂，它接受一个字符串 config_name ，并将其转换为配置对象的名称
def create_app(config_name):
    app = Flask(__name__)

    # 如果 config_name 是 development ，那么变量 config_module 将变为 application.config.DevelopmentConfig，
    # 以便 app.config.from_object 可以导入它
    config_module = f"application.config.{config_name.capitalize()}Config"

    app.config.from_object(config_module)

    from application.models import db, migrate

    # 导入，获取配置并初始化数据库和迁移对象
    db.init_app(app)
    migrate.init_app(app, db)

    # 快速检查服务器是否正常运行
    @app.route("/")
    def hello_world():
        return "Hello, World!"

    # 导入模型 User 并统计其表中的记录数量
    @app.route("/users")
    def users():
        num_users = User.query.count()
        return f"Number of users: {num_users}"

    return app
