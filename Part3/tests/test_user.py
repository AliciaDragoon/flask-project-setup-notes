# 简易tdd测试
from application.models import User


# 测试在数据库中创建一个用户，然后检索该用户并检查其属性
def test__create_user(database):
    email = "some.email@server.com"
    user = User(email=email)
    database.session.add(user)
    database.session.commit()

    user = User.query.first()

    # 如果model中没有User类，或者User类没有email属性，运行此测试会报错
    assert user.email == email
