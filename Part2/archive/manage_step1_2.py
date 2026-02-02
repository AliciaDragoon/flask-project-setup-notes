# 添加数据库容器，连接应用与数据库
import os
import json
import signal
import subprocess
import time

# click是实现 Flask 命令的推荐方式
import click
import psycopg
from psycopg import sql  # 用于安全的 SQL 标识符拼接

# docker_compose_file = "docker/development.yml"
# # Docker Compose V2 语法
# docker_compose_cmdline = ["docker", "compose", "-f", docker_compose_file]


# 确保环境变量存在且具有值
def setenv(variable, default):
    os.environ[variable] = os.getenv(variable, default)


# 设置应用程序配置环境变量的默认值
setenv("APPLICATION_CONFIG", "development")

# # 从相对的JSON文件中读取配置
# config_json_filename = os.getenv("APPLICATION_CONFIG") + ".json"
# with open(os.path.join("config", config_json_filename)) as f:
#     config = json.load(f)

# # 将配置转换为可用的 Python 字典
# config = dict((i["name"], i["value"]) for i in config)

# for key, value in config.items():
#     setenv(key, value)
# # print(f"DEBUG: APPLICATION_CONFIG = {os.getenv('APPLICATION_CONFIG')}")
# # print(f"DEBUG: FLASK_CONFIG = {os.getenv('FLASK_CONFIG')}")


# 在configure_app函数中封装配置逻辑
def configure_app(config):
    # 从相对的JSON文件中读取配置
    with open(os.path.join("config", f"{config}.json")) as f:
        config_data = json.load(f)

    # # 将此配置转换为可用的Python字典
    # config_data = dict((i["name"], i["value"]) for i in config_data)

    # for key, value in config_data.items():
    #     setenv(key, value)

    # 使用字典推导式
    config_dict = {item["name"]: item["value"] for item in config_data}

    for key, value in config_dict.items():
        setenv(key, value)


@click.group()
def cli():
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=click.Path())
# 对 Flask 提供的命令 flask 封装，以便通过 ./manage.py flask SUBCOMMAND 使用配置 development 运行，
# 或使用 APPLICATION_CONFIG="foobar" ./manage.py flask SUBCOMMAND 采用 foobar 配置。
def flask(subcommand):
    cmdline = ["flask"] + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


# 构建 Docker Compose 命令行，支持可选的命令字符串参数
def docker_compose_cmdline(config):
    configure_app(os.getenv("APPLICATION_CONFIG"))

    docker_compose_file = os.path.join("docker", f"{config}.yml")

    if not os.path.isfile(docker_compose_file):
        raise ValueError(f"The file {docker_compose_file} does not exist")

    return [
        "docker",
        "compose",
        "-p",  # 为容器添加前缀，以在运行开发服务器的同时执行测试
        config,
        "-f",
        docker_compose_file,
    ]


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=str)
def compose(subcommand):
    cmdline = docker_compose_cmdline + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


def run_sql(statements):
    """
    执行 SQL 语句列表
    支持安全的标识符拼接（通过 sql.Composable）
    """
    conn = psycopg.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOSTNAME"),
        port=os.getenv("POSTGRES_PORT"),
    )

    # psycopg3 新的自动提交设置方式
    conn.autocommit = True

    with conn.cursor() as cursor:
        for statement in statements:
            if isinstance(statement, sql.Composable):
                # 如果是 psycopg.sql 对象（如 Identifier 包裹的）
                cursor.execute(statement)
            else:
                # 普通字符串（兼容性保留，但不推荐用于 DDL）
                cursor.execute(statement)

    conn.close()


def wait_for_logs(cmdline, message, timeout=30):
    """
    轮询日志等待特定消息出现
    添加超时防止无限等待
    """
    start_time = time.time()
    while True:
        logs = subprocess.check_output(cmdline)
        if message in logs.decode("utf-8"):
            return True

        if time.time() - start_time > timeout:
            raise TimeoutError(f"等待日志消息 '{message}' 超时（{timeout}秒）")

        time.sleep(0.1)


@cli.command()
def create_initial_db():
    configure_app(os.getenv("APPLICATION_CONFIG"))

    db_name = os.getenv("APPLICATION_DB")

    try:
        # 使用安全的 SQL 标识符拼接，防止特殊字符问题
        query = sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name))
        run_sql([query])
        print(f"Database '{db_name}' created successfully")
    except psycopg.errors.DuplicateDatabase:
        print(f"The database '{db_name}' already exists and will not be recreated")


# cli.add_command(flask)
@cli.command()
@click.argument("filenames", nargs=-1)
def test(filenames):
    # 加载文件 config/testing.json 中的配置
    os.environ["APPLICATION_CONFIG"] = "testing"
    configure_app(os.getenv("APPLICATION_CONFIG"))

    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["up", "-d"]
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["logs", "db"]
    logs = subprocess.check_output(cmdline)
    # 在运行测试前，脚本会等待服务就绪
    while "ready to accept connections" not in logs.decode("utf-8"):
        time.sleep(0.1)
        logs = subprocess.check_output(cmdline)

    cmdline = ["pytest", "-svv", "--cov=application", "--cov-report=term-missing"]
    cmdline.extend(filenames)
    subprocess.call(cmdline)

    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["down"]
    subprocess.call(cmdline)


if __name__ == "__main__":
    cli()
