FROM python:3.12-slim

ENV PYTHONUNBUFFERED 1

RUN mkdir /opt/code
RUN mkdir /opt/requirements
WORKDIR /opt/code

ADD requirements /opt/requirements
# 安装开发环境的依赖
RUN pip install -r /opt/requirements/development.txt