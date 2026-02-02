# 定义数据结构和数据库实例（不关心配置）
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate


# 创建空实例（无配置）
db = SQLAlchemy()
migrate = Migrate()


class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String, unique=True, nullable=False)
