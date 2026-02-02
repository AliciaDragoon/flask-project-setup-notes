# 配置 Flask 应用程序。统一管理不同环境下的配置。
class Config(object):
    """基础环境"""


class ProductionConfig(Config):
    """生产环境"""


class DevelopmentConfig(Config):
    """开发环境"""


class TestingConfig(Config):
    """测试环境"""

    TESTING = True
