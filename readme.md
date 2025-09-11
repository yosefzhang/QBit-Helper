# QBitTorrent Helper

一个基于 Flask 的 qBittorrent 管理助手，用于自动化处理种子标签和跟踪器。

## 功能特性

- **仪表盘**: 查看 qBittorrent 的总体统计信息，包括种子数、Tracker 数、异常 Tracker 数以及分类和标签统计
- **任务管理**: 创建和管理自动任务，支持手动执行和定时执行
- **规则配置**: 
  - 标签规则: 根据 Tracker 关键字匹配种子并添加或删除标签
  - 跟踪器规则: 根据标签匹配种子并添加或删除跟踪器
  - 辅种标记规则: 自动识别并标记辅种
- **通知功能**: 集成 Server酱 推送通知
- **Web UI**: 基于 Bootstrap 5 的响应式界面，支持暗色主题

## 项目结构

```
qbit-helper/
├─ app.py                 # Flask 应用主文件
├─ qbit_helper.py         # 核心功能实现
├─ requirements.txt       # 项目依赖
├─ readme.md              # 项目说明文档
└─ data/
   ├─ QBittorrent-Helper.log  # 运行日志
   ├─ config.yaml             # 用户配置文件
   └─ config_example.yaml     # 配置示例文件
└─ ui/
   ├─ css/
   │  └─ styles.css           # 自定义样式
   ├─ js/
   │  ├─ bootstrap.bundle.min.js  # Bootstrap JS
   │  └─ scripts.js               # 自定义脚本
   └─ templates/
      ├─ dashboard.html      # 仪表盘页面
      ├─ layout.html         # 页面布局模板
      ├─ settings.html       # 设置页面
      └─ tasks.html          # 任务页面
```

## 安装部署

### 环境要求

- Python 3.7+
- qBittorrent v4.1+

### 方式一：传统部署

1. 克隆项目到本地：
   ```bash
   git clone <repository-url>
   cd qbit-helper
   ```

2. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

3. 配置 qBittorrent：
   - 确保 qBittorrent 正在运行
   - 在 qBittorrent 设置中启用 Web UI
   - 记录 Web UI 的访问地址、用户名和密码

4. 配置应用：
   - 复制 `data/config_example.yaml` 到 `data/config.yaml`
   - 修改 `data/config.yaml` 中的 qBittorrent 连接信息

5. 启动应用：
   ```bash
   python app.py
  
   ```
   推荐使用Gunicorn启动应用
   ```bash
      gunicorn --bind 0.0.0.0:8080 --workers 4 app:app
   ```

6. 访问 Web 界面：
   - 打开浏览器访问 `http://localhost:5000`

### 方式二：Docker部署（推荐）

1. 确保已安装 Docker 和 Docker Compose

2. 构建并启动容器：
   ```bash
   docker-compose up -d
   ```

3. 配置 qBittorrent：
   - 确保 qBittorrent 正在运行
   - 在 qBittorrent 设置中启用 Web UI
   - 记录 Web UI 的访问地址、用户名和密码

4. 配置应用：
   - 复制 `data/config_example.yaml` 到 `data/config.yaml`
   - 修改 `data/config.yaml` 中的 qBittorrent 连接信息

5. 访问 Web 界面：
   - 打开浏览器访问 `http://localhost:5000`

### 方式三：直接使用Docker镜像

1. 拉取镜像并运行容器：
   ```bash
   docker run -d \
     --name qbit-helper \
     -p 5000:5000 \
     -v $(pwd)/data:/app/data \
     your-image-name
   ```

2. 配置步骤同方式二的第3-5步

## 使用说明

### 配置 qBittorrent 连接

1. 进入"设置"页面
2. 在"配置"部分填写 qBittorrent 的连接信息：
   - 主机：qBittorrent Web UI 的地址（如 http://192.168.0.123:8085）
   - 用户名和密码：qBittorrent Web UI 的登录凭据
3. 点击"保存配置"按钮

### 配置 Server酱通知（可选）

1. 在"设置"页面的"配置"部分填写 Server酱 的 send key
2. 点击"保存配置"按钮

### 创建规则

1. 进入"设置"页面
2. 在"规则"部分点击"新增规则"按钮
3. 选择规则类型：
   - 处理标签：根据 Tracker 关键字匹配种子并添加或删除标签
   - 处理跟踪器：根据标签匹配种子并添加或删除跟踪器
   - 标记辅种：自动识别并标记辅种
4. 填写规则信息：
   - 规则名称：自定义规则名称
   - 操作类型：添加或删除
   - 优先级：1-99，值越小优先级越高
   - 匹配条件：根据规则类型填写相应的匹配条件
5. 点击"保存"按钮

### 创建任务

1. 进入"任务"页面
2. 点击"新增任务"按钮
3. 填写任务信息：
   - 任务名称：自定义任务名称
   - 任务类型：手动或自动
   - Cron表达式：自动任务的执行时间表达式（仅自动任务需要填写）
   - 选择规则：选择该任务要执行的规则
4. 点击"保存任务"按钮

### 执行任务

- 手动执行：在任务列表中点击任务的"执行"按钮
- 自动执行：根据任务配置的 Cron 表达式自动执行

## 技术架构

### 后端

- **Flask**: Web 框架
- **qbittorrent-api**: 与 qBittorrent Web API 交互
- **PyYAML**: 配置文件解析
- **APScheduler**: 任务调度

### 前端

- **Bootstrap 5**: UI 框架
- **Bootstrap Icons**: 图标库
- **原生 JavaScript**: 交互逻辑

## API 接口

### 配置相关

- `GET /api/config/get_user_config`: 获取用户配置
- `POST /api/config/save_user_config`: 保存用户配置
- `GET /api/config/get_user_rules`: 获取用户规则
- `POST /api/config/save_user_rules`: 保存用户规则
- `GET /api/config/get_user_tasks`: 获取用户任务
- `POST /api/config/save_user_tasks`: 保存用户任务
- `POST /api/config/reload_config`: 重载配置

### 任务相关

- `POST /api/task/execute_manual_task`: 执行手动任务
- `POST /api/task/toggle_auto_task`: 启用/禁用自动任务

### 仪表盘相关

- `GET /api/dashboard/info`: 获取仪表盘信息

## 日志

应用日志保存在 `data/QBittorrent-Helper.log` 文件中，包含以下信息：
- 应用启动和配置加载
- 与 qBittorrent 的连接状态
- 任务执行详情
- 错误信息

## 故障排除

### 连接问题

- 检查 qBittorrent Web UI 是否已启用
- 确认配置文件中的主机地址、用户名和密码是否正确
- 检查网络连接是否正常

### 任务执行问题

- 查看日志文件了解详细错误信息
- 确认规则配置是否正确
- 检查 qBittorrent 是否正常运行

## 许可证

MIT License