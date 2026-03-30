# SecondBrain Docker 镜像

FROM python:3.10-slim

WORKDIR /app

# 复制项目文件
COPY . .

# 安装依赖
RUN pip install -r requirements.txt

# 安装 SecondBrain
RUN pip install -e .

# 暴露端口
EXPOSE 8000

# 启动应用
CMD ["secondbrain"]
