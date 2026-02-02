import pytest

from application.app import create_app
from application.models import db


# @pytest.fixture 装饰的函数可以被项目中的所有测试文件自动访问，无需导入
@pytest.fixture
# 便于其他 fixture 使用。
def app():
    # 创建测试环境的应用实例
    app = create_app("testing")

    return app


@pytest.fixture(scope="function")
# 用于与数据库本身交互
def database(app):
    with app.app_context():
        # 重置数据库，防止上一次测试的函数留下脏数据
        db.drop_all()  # 清理数据库
        db.create_all()  # 创建所有表

    yield db  # 提供数据库连接给测试使用
