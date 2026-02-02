《Flask project setup: TDD, Docker, Postgres and more》学习笔记

博客地址：https://www.thedigitalcatonline.com/blog/2020/07/05/flask-project-setup-tdd-docker-postgres-and-more-part-1/

项目搭建的主要需求：

开发、测试、生产环境使用相同的数据库引擎（Postgres）；

测试使用临时数据库（ephemeral database）；

生产部署仅需修改静态配置，无需改动代码；

能够初始化数据库、管理迁移；

能从空数据库快速创建"场景"（scenarios）用于测试查询；

本地环境能模拟生产环境。

配置必须单一来源（Single Source of Truth），使用 JSON 格式（可被 Python、Terraform、AWS ECS 等多种工具读取）。

作者特别提醒：不要被"想快速看到效果"的冲动驱使而忽略了基础架构。


第一章通过一个建立一个部署友好（deploy-friendly）、环境一致的Flask 项目现代化开发环境展示了"基础设施即代码"的思维，在项目初期就建立一个部署友好（deploy-friendly）、环境一致的开发架构，可以避免后期技术债务
搭建流程：
- 第1步：依赖管理与编辑器配置
创建三层 requirements 结构：production.txt（最简依赖）← development.txt（开发工具）← testing.txt（测试包）
使用ruff进行代码风格检查
（使用UV）创建虚拟环境
- 第2步：Flask 项目样板
应用工厂模式：create_app(config_name) 函数动态加载配置类
配置分层：基类 Config → ProductionConfig / DevelopmentConfig / TestingConfig（继承避免重复）
环境变量区分：
FLASK_DEBUG：Flask 2.3完全移除对 FLASK_ENV 环境变量的支持，FLASK_DEBUG=1 会自动启用调试服务器的重载（reload）和调试器（debugger）
FLASK_CONFIG：自定义，用于选择配置类名
WSGI 入口：wsgi.py 文件，兼容 Gunicorn/uWSGI 等生产服务器
- 第3步：配置系统与管理脚本
JSON 配置文件：config/development.json 存储环境变量（如 FLASK_DEBUG, FLASK_CONFIG）
manage.py 管理脚本：使用 click 库创建 CLI 工具
读取 JSON 并转换为环境变量
包装 flask 命令：`./manage.py flask run`
通过 APPLICATION_CONFIG 变量切换配置（如 production）
- 第4步：Docker 容器化
Dockerfile：基于 python:3.12-slim，安装依赖，代码目录运行时挂载`docker compose -f docker/development.yml up` 定义服务，在yml文件中传递环境变量
管理脚本集成：在 manage.py 中添加 compose 命令，读取环境变量，即config/development.json 中的值
构建：`./manage.py compose build`
运行：`./manage.py compose up -d`
进入容器：`./manage.py compose exec web bash`
注意：在Windows中使用 `python manage.py` 而非 `./manage.py`


第二章在开发环境和测试环境中，通过 Docker 容器运行一个生产就绪的数据库，与你的代码并行运行，展示了良好的项目结构能带来多大的不同。项目结构清晰，将命令封装在管理脚本中并采用集中式配置，可以以一种优雅的方式解决迁移和测试的问题。
搭建流程：
- 第1步：添加数据库容器
在 docker/development.yml 中添加 db 服务（Postgres 官方镜像）
配置持久化卷 pgdata 防止数据丢失
通过环境变量传递数据库配置（POSTGRES_DB, POSTGRES_USER 等）
关键概念：区分 POSTGRES_DB（Postgres 默认管理库）和 APPLICATION_DB（应用实际使用的库）
- 第2步：连接应用与数据库
使用 Flask-SQLAlchemy 作为 ORM，Flask-Migrate（基于 Alembic）处理数据库迁移
在 config.py 中构建 SQLAlchemy URI：postgresql+psycopg://...
解决容器间通信：Web 容器通过服务名 db 访问数据库（Docker Compose 内置 DNS）
初始化迁移仓库：./manage.py flask db init
- 第3步：搭建测试环境
创建独立的 docker/testing.yml 配置，使用不同端口（5433）避免与开发环境冲突
编写 manage.py test 命令实现：
启动测试数据库容器
等待数据库就绪（轮询日志检测 "ready to accept connections"）
运行 pytest 并生成覆盖率报告
清理容器
- 第4步：初始化测试数据库
创建 create_initial_db 命令，使用 psycopg2 直接执行 SQL 创建数据库
重构 manage.py，提取 docker_compose_cmdline, wait_for_logs 等通用函数
- 第5步：测试夹具（Fixtures）
在 tests/conftest.py 中定义：
app fixture：创建测试配置的应用实例
database fixture：每个测试函数前清理并重建表结构（db.drop_all() → db.create_all()）
- 第6步：TDD 示例（Bonus）
完整的测试驱动开发流程：编写测试 → 运行失败 → 实现 User 模型 → 测试通过
演示如何创建迁移脚本并应用到开发数据库
注意，每次在本地安装依赖后记得运行 `pip install -r requirements/development.txt` ，并运行 `./manage.py compose build web` 重新构建镜像（修改代码后也要运行）

第三章通过如何轻松创建仅包含特定数据的数据库场景，即动态生成包含自定义数据的数据库，来进行查询测试。
搭建流程：
- 第1步：测试场景系统（Scenarios）
创建 manage.py scenario up/down 命令来管理临时测试数据库
通过动态分配 Docker 端口（随机端口映射）避免与开发/测试数据库冲突
场景文件位于 scenarios/ 目录，可自定义填充数据用于调试特定用例
- 第2步：生产环境模拟
用 Gunicorn 替代 Flask 开发服务器（gunicorn -w 4 -b 0.0.0.0 wsgi:app）
创建生产环境 Docker Compose 和 Dockerfile 配置
使用 Postgres 并配置持久化卷（pgdata）
- 第3步：扩展与负载均衡
添加 Nginx 作为反向代理（监听 8080 端口）
展示 Docker Compose 扩缩容：--scale web=3
解释 Docker 内部 DNS 解析机制（通过 dig web 查看多容器 IP）
- 第4步：部署建议
提及 AWS ECS、Terraform、CI/CD (Jenkins/CircleCI) 等生产工具
