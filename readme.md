# 《Flask project setup: TDD, Docker, Postgres and more》学习笔记

**博客地址：** https://www.thedigitalcatonline.com/blog/2020/07/05/flask-project-setup-tdd-docker-postgres-and-more-part-1/

## 项目核心需求

- 开发、测试、生产环境使用相同的数据库引擎（Postgres）
- 测试使用临时数据库（ephemeral database）
- 生产部署仅需修改静态配置，无需改动代码
- 能够初始化数据库、管理迁移
- 能从空数据库快速创建"场景"（scenarios）用于测试查询
- 本地环境能模拟生产环境
- **配置必须单一来源（Single Source of Truth）**，使用 JSON 格式（可被 Python、Terraform、AWS ECS 等多种工具读取）

> 💡 **作者提醒：** 不要被"想快速看到效果"的冲动驱使而忽略了基础架构。

---

## 第一章：基础设施即代码

> 通过一个部署友好（deploy-friendly）、环境一致的 Flask 项目现代化开发环境，展示"基础设施即代码"的思维。在项目初期建立部署友好、环境一致的开发架构，可以避免后期技术债务。

### 第1步：依赖管理与编辑器配置

| 层级 | 文件 | 用途 |
|------|------|------|
| 基础 | `production.txt` | 最简依赖 |
| 开发 | `development.txt` | 开发工具 |
| 测试 | `testing.txt` | 测试包 |

- 使用 **ruff** 进行代码风格检查
- 使用 **UV** 创建虚拟环境

### 第2步：Flask 项目样板

**应用工厂模式**
```python
create_app(config_name)  # 动态加载配置类
```

**配置分层**
```
Config（基类）
├── ProductionConfig
├── DevelopmentConfig
└── TestingConfig
```

**关键环境变量**

| 变量 | 说明 |
|------|------|
| `FLASK_DEBUG` | Flask 2.3+ 完全移除对 `FLASK_ENV` 的支持，`FLASK_DEBUG=1` 自动启用调试服务器的重载（reload）和调试器（debugger） |
| `FLASK_CONFIG` | 自定义，用于选择配置类名 |

**WSGI 入口：** `wsgi.py` 文件，兼容 Gunicorn/uWSGI 等生产服务器

### 第3步：配置系统与管理脚本

- **JSON 配置文件：** `config/development.json` 存储环境变量（如 `FLASK_DEBUG`, `FLASK_CONFIG`）
- **管理脚本：** `manage.py` 使用 click 库创建 CLI 工具
  - 读取 JSON 并转换为环境变量
  - 包装 flask 命令：`./manage.py flask run`
  - 通过 `APPLICATION_CONFIG` 变量切换配置（如 production）

### 第4步：Docker 容器化

**Dockerfile：** 基于 `python:3.12-slim`，安装依赖，代码目录运行时挂载

**运行命令：**
```bash
# 定义服务（在 yml 文件中传递环境变量）
docker compose -f docker/development.yml up

# 管理脚本集成
./manage.py compose build    # 构建
./manage.py compose up -d    # 运行
./manage.py compose exec web bash  # 进入容器
```

> ⚠️ **注意：** Windows 中使用 `python manage.py` 而非 `./manage.py`

---

## 第二章：数据库与测试环境

> 在开发环境和测试环境中，通过 Docker 容器运行生产就绪的数据库，与代码并行运行。清晰的项目结构 + 命令封装在管理脚本中 + 集中式配置 = 优雅解决迁移和测试问题。

### 第1步：添加数据库容器

在 `docker/development.yml` 中添加 `db` 服务：
- 使用 Postgres 官方镜像
- 配置持久化卷 `pgdata` 防止数据丢失
- 通过环境变量传递数据库配置（`POSTGRES_DB`, `POSTGRES_USER` 等）

> **关键概念：** 区分 `POSTGRES_DB`（Postgres 默认管理库）和 `APPLICATION_DB`（应用实际使用的库）

### 第2步：连接应用与数据库

- **ORM：** Flask-SQLAlchemy
- **迁移：** Flask-Migrate（基于 Alembic）
- **URI 格式：** `postgresql+psycopg://...`
- **容器通信：** Web 容器通过服务名 `db` 访问数据库（Docker Compose 内置 DNS）

**初始化迁移仓库：**
```bash
./manage.py flask db init
```

### 第3步：搭建测试环境

- 创建独立的 `docker/testing.yml` 配置
- 使用不同端口（`5433`）避免与开发环境冲突

**测试命令流程：**
1. 启动测试数据库容器
2. 等待数据库就绪（轮询日志检测 `"ready to accept connections"`）
3. 运行 pytest 并生成覆盖率报告
4. 清理容器

### 第4步：初始化测试数据库

- 创建 `create_initial_db` 命令
- 使用 `psycopg2` 直接执行 SQL 创建数据库
- 重构 `manage.py`，提取 `docker_compose_cmdline`, `wait_for_logs` 等通用函数

### 第5步：测试夹具（Fixtures）

在 `tests/conftest.py` 中定义：

| Fixture | 作用 |
|---------|------|
| `app` | 创建测试配置的应用实例 |
| `database` | 每个测试函数前清理并重建表结构（`db.drop_all()` → `db.create_all()`）|

### 第6步：TDD 示例（Bonus）

**完整 TDD 流程：**
1. 编写测试 → 2. 运行失败 → 3. 实现 User 模型 → 4. 测试通过

演示如何创建迁移脚本并应用到开发数据库

> ⚠️ **注意：** 每次在本地安装依赖后记得运行 `pip install -r requirements/development.txt`，并运行 `./manage.py compose build web` 重新构建镜像（修改代码后也要运行）

---

## 第三章：场景系统与生产模拟

> 如何轻松创建仅包含特定数据的数据库场景，即动态生成包含自定义数据的数据库，来进行查询测试。

### 第1步：测试场景系统（Scenarios）

**管理命令：**
```bash
./manage.py scenario up    # 启动场景
./manage.py scenario down  # 关闭场景
```

**特点：**
- 动态分配 Docker 端口（随机端口映射），避免与开发/测试数据库冲突
- 场景文件位于 `scenarios/` 目录，可自定义填充数据用于调试特定用例

### 第2步：生产环境模拟

- 用 **Gunicorn** 替代 Flask 开发服务器
  ```bash
  gunicorn -w 4 -b 0.0.0.0 wsgi:app
  ```
- 创建生产环境 Docker Compose 和 Dockerfile 配置
- 使用 Postgres 并配置持久化卷（`pgdata`）

### 第3步：扩展与负载均衡

- **Nginx：** 作为反向代理（监听 8080 端口）
- **Docker Compose 扩缩容：** `--scale web=3`
- **内部 DNS 解析：** 通过 `dig web` 查看多容器 IP

### 第4步：平台部署建议

AWS ECS、Terraform、CI/CD (Jenkins/CircleCI)
