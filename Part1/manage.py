import os
import json
import signal
import subprocess

# click是实现 Flask 命令的推荐方式
import click

docker_compose_file = "docker/development.yml"
# Docker Compose V2 语法
docker_compose_cmdline = ["docker", "compose", "-f", docker_compose_file]


# 确保环境变量存在且具有值
def setenv(variable, default):
    os.environ[variable] = os.getenv(variable, default)


# 设置应用程序配置环境变量的默认值
setenv("APPLICATION_CONFIG", "development")

# 从相对的JSON文件中读取配置
config_json_filename = os.getenv("APPLICATION_CONFIG") + ".json"
with open(os.path.join("config", config_json_filename)) as f:
    config = json.load(f)

# 将配置转换为可用的 Python 字典
config = dict((i["name"], i["value"]) for i in config)

for key, value in config.items():
    setenv(key, value)
# print(f"DEBUG: APPLICATION_CONFIG = {os.getenv('APPLICATION_CONFIG')}")
# print(f"DEBUG: FLASK_CONFIG = {os.getenv('FLASK_CONFIG')}")


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


@cli.command(context_settings={"ignore_unknown_options": True})
# @click.argument("subcommand", nargs=-1, type=click.Path())
@click.argument("subcommand", nargs=-1, type=str)
def compose(subcommand):
    cmdline = docker_compose_cmdline + list(subcommand)

    try:
        p = subprocess.Popen(cmdline)
        p.wait()
    except KeyboardInterrupt:
        p.send_signal(signal.SIGINT)
        p.wait()


cli.add_command(flask)

if __name__ == "__main__":
    cli()

# 测试命令：
# uv run python manage.py flask run
