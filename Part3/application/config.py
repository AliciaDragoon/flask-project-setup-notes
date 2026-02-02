# 配置 Flask 应用程序。统一管理不同环境下的配置。
import os


class Config(object):
    """基础环境"""

    user = os.environ["POSTGRES_USER"]
    password = os.environ["POSTGRES_PASSWORD"]
    hostname = os.environ["POSTGRES_HOSTNAME"]
    port = os.environ["POSTGRES_PORT"]
    # 将 Postgres 用于管理所有其他数据库的默认数据库，与我们的应用程序专用的数据库分离开来
    database = os.environ["APPLICATION_DB"]

    # 使用psycopg3
    SQLALCHEMY_DATABASE_URI = (
        f"postgresql+psycopg://{user}:{password}@{hostname}:{port}/{database}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False


class ProductionConfig(Config):
    """生产环境"""


class DevelopmentConfig(Config):
    """开发环境"""


class TestingConfig(Config):
    """测试环境"""

    TESTING = True
