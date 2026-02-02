# 搭建测试环境
import os
import json
import signal
import subprocess
import time

# click是实现 Flask 命令的推荐方式
import click


# 确保环境变量存在且具有值
def setenv(variable, default):
    os.environ[variable] = os.getenv(variable, default)


# 设置应用程序配置环境变量的默认值
setenv("APPLICATION_CONFIG", "development")


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
    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


@cli.command()
@click.argument("filenames", nargs=-1)
def test(filenames):
    # 加载文件 config/testing.json 中的配置
    os.environ["APPLICATION_CONFIG"] = "testing"
    configure_app(os.getenv("APPLICATION_CONFIG"))

    # 构建 Docker Compose 命令行，-d 参数表示在后台运行容器
    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["up", "-d"]
    subprocess.call(cmdline)

    # 获取数据库容器的日志
    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["logs", "db"]
    logs = subprocess.check_output(cmdline)

    # 确保数据库完全启动后再运行测试
    while "ready to accept connections" not in logs.decode("utf-8"):
        # 如果没找到，等待 0.1 秒后再次检查
        time.sleep(0.1)
        logs = subprocess.check_output(cmdline)

    # 运行测试
    cmdline = ["pytest", "-svv", "--cov=application", "--cov-report=term-missing"]
    cmdline.extend(filenames)
    subprocess.call(cmdline)

    # 停止并移除所有测试容器。确保每次测试后环境干净，不会留下残留的容器
    cmdline = docker_compose_cmdline(os.getenv("APPLICATION_CONFIG")) + ["down"]
    subprocess.call(cmdline)


if __name__ == "__main__":
    cli()
