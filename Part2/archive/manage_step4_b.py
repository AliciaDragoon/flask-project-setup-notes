# 初始化测试数据库(下)
import os
import json
import signal
import subprocess
import time

# click是实现 Flask 命令的推荐方式
import click

import psycopg


# 确保环境变量存在且具有值
def setenv(variable, default):
    os.environ[variable] = os.getenv(variable, default)


# 设置应用程序配置环境变量的默认值
setenv("APPLICATION_CONFIG", "development")

APPLICATION_CONFIG_PATH = "config"
DOCKER_PATH = "docker"


# 封装文件路径的创建
def app_config_file(config):
    return os.path.join(APPLICATION_CONFIG_PATH, f"{config}.json")


def docker_compose_file(config):
    return os.path.join(DOCKER_PATH, f"{config}.yml")


# 在configure_app函数中封装配置逻辑
def configure_app(config):
    # 从相对的JSON文件中读取配置
    with open(os.path.join("config", f"{config}.json")) as f:
        config_data = json.load(f)

    # 将此配置转换为可用的Python字典
    config_data = dict((i["name"], i["value"]) for i in config_data)

    for key, value in config_data.items():
        setenv(key, value)


@click.group()
def cli():
    pass


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=click.Path())
# 对 Flask 提供的命令 flask 封装，以便通过 ./manage.py flask SUBCOMMAND 使用配置 development 运行
def flask(subcommand):
    configure_app(os.getenv("APPLICATION_CONFIG"))

    cmdline = ["flask"] + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


# 构建 Docker Compose 命令行，接收一个字符串，并在内部将其转换为列表
def docker_compose_cmdline(commands_string=None):
    config = os.getenv("APPLICATION_CONFIG")
    configure_app(config)

    compose_file = docker_compose_file(config)

    if not os.path.isfile(compose_file):
        raise ValueError(f"The file {compose_file} does not exist")

    command_line = [
        "docker",
        "compose",
        "-p",  # 为容器添加前缀，以在运行开发服务器的同时执行测试
        config,
        "-f",
        compose_file,
    ]

    if commands_string:
        command_line.extend(commands_string.split(" "))

    return command_line


@cli.command(context_settings={"ignore_unknown_options": True})
@click.argument("subcommand", nargs=-1, type=str)
def compose(subcommand):
    cmdline = docker_compose_cmdline() + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


# 与 PostgreSQL 建立连接并执行传入的指令
def run_sql(statements):
    # 从JSON 配置文件中加载环境变量并连接到 PostgreSQL 服务器
    conn = psycopg.connect(
        dbname=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOSTNAME"),
        port=os.getenv("POSTGRES_PORT"),
    )
    # 自动提交每个语句
    conn.autocommit = True
    # 创建一个游标对象
    cursor = conn.cursor()
    # 使用游标循环执行列表里的每一条 SQL 语句
    for statement in statements:
        cursor.execute(statement)

    # 手动关闭游标和连接，防止内存泄漏或连接数占满
    cursor.close()
    conn.close()


# 将等待数据库容器日志中消息的代码隔离出来
def wait_for_logs(cmdline, message):
    logs = subprocess.check_output(cmdline)
    while message not in logs.decode("utf-8"):
        time.sleep(0.1)
        logs = subprocess.check_output(cmdline)


# 创建测试数据库
@cli.command()
def create_initial_db():
    # 环境配置
    configure_app(os.getenv("APPLICATION_CONFIG"))

    try:
        # 创建一个名为 XXX 的数据库
        run_sql([f"CREATE DATABASE {os.getenv('APPLICATION_DB')}"])
    except psycopg.errors.DuplicateDatabase:
        # 如果是第二次运行，PostgreSQL 会报错说“数据库已存在”
        print(
            f"The database {os.getenv('APPLICATION_DB')} already exists and will not be recreated"
        )


@cli.command()
@click.argument("filenames", nargs=-1)
def test(filenames):
    # 加载文件 config/testing.json 中的配置
    os.environ["APPLICATION_CONFIG"] = "testing"
    configure_app(os.getenv("APPLICATION_CONFIG"))

    # 构建 Docker Compose 命令行，-d 参数表示在后台运行容器
    cmdline = docker_compose_cmdline("up -d")
    subprocess.call(cmdline)

    # 获取数据库容器的日志
    cmdline = docker_compose_cmdline("logs db")
    
    # 确保数据库完全启动后再运行测试
    wait_for_logs(cmdline, "ready to accept connections")
    
    # 创建测试数据库
    run_sql([f"CREATE DATABASE {os.getenv('APPLICATION_DB')}"])
    
    # 运行测试
    cmdline = ["pytest", "-svv", "--cov=application", "--cov-report=term-missing"]
    cmdline.extend(filenames)
    subprocess.call(cmdline)

    # 停止并移除所有测试容器。确保每次测试后环境干净，不会留下残留的容器
    cmdline = docker_compose_cmdline("down")
    subprocess.call(cmdline)


if __name__ == "__main__":
    cli()
