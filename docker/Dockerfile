# 使用Python 3.11作为基础镜像
FROM python:3.11-slim

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# 复制requirements.txt并安装依赖
ENV http_proxy=http://192.168.0.123:7890
ENV https_proxy=http://192.168.0.123:7890
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY ./data/config_example.yaml /app/data/
COPY ./ui /app/ui/
COPY *.py /app/
COPY ./readme.md /app/
COPY ./requirements.txt /app/
COPY ./LICENSE /app/

# 创建data目录（如果不存在）
RUN mkdir -p data

# 暴露端口
EXPOSE 8080

# 设置环境变量
ENV PYTHONPATH=/app

# 使用Gunicorn启动应用
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "app:app"]