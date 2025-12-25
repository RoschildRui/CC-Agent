# MarketPulse - AI 驱动的产品市场分析系统

> **版本**: v1.1 (2025-12-23 更新)
> **状态**: 开源版本

基于 Flask 的 Web 应用，利用多个 AI 模型和 Web 搜索技术，帮助创业者优化产品定义、生成真实用户画像，并模拟潜在用户对产品的反应，提供全面的产品市场分析报告。

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-repo/polyscore.git
cd polyscore
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp env_example.txt .env

# 编辑 .env 文件，填入你的 API 密钥
```

### 3. 安装依赖并运行

```bash
# 推荐：使用 uv（更快、更稳定）
# 1) 安装 uv
# macOS / Linux:
curl -LsSf https://astral.sh/uv/install.sh | sh
# Windows PowerShell:
# irm https://astral.sh/uv/install.ps1 | iex

# 2) 创建虚拟环境并安装依赖
uv venv
uv pip install -r requirements.txt

# 3) 激活环境变量
# max/linux
source .venv/bin/activate
# window
.\.venv\Scripts\activate

# 4) 运行应用
python app.py

# 或使用一键脚本 (Linux/Mac)
./setup.sh

# Windows 用户
start_product_analyzer.bat
```

> 说明：`uv venv` 会创建 `.venv/`，你也可以先激活虚拟环境再运行 `python app.py`。
> - macOS/Linux: `source .venv/bin/activate`
> - Windows: `.\.venv\Scripts\activate`

### 4. 访问应用

打开浏览器访问：http://localhost:5001

---

## 核心功能

### 1. AI 辅助产品描述优化
- **智能对话引导**：通过多轮 AI 对话，逐步明确产品定义
- **Web 搜索增强**：自动搜索相关市场信息，提供实时参考资料
- **上下文理解**：AI 助手能够理解产品领域，给出专业建议

### 2. 智能用户画像生成
- **多样性保证**：通过多轮验证机制，确保生成的用户画像多样且真实
- **质量审查**：AI 审查员自动识别并修正不合理的画像
- **详细刻画**：包含年龄、职业、需求、痛点、使用习惯等多维度信息

### 3. 用户反应模拟
- **真实场景模拟**：基于用户画像，模拟真实使用场景和反馈
- **多角度评估**：从需求强度、使用意愿、依赖程度等维度评估
- **情感化反馈**：生成符合画像特征的自然语言反馈

### 4. 数据可视化报告
- **关键指标分析**：
  - **刚需比例**：有强烈需求的用户占比
  - **依赖度**：用户对产品的依赖程度分布
  - **使用意愿**：不同画像的使用倾向
- **交互式图表**：使用 Chart.js 生成美观的数据图表
- **详细画像卡片**：每个用户画像的完整分析
- **Web 搜索参考资料**：在报告末尾提供所有搜索引用来源

### 5. 实时 Web 搜索集成
- **Bocha AI 搜索**：集成博查 AI 搜索引擎，提供最新市场信息
- **智能查询生成**：根据产品描述自动生成相关搜索查询
- **结果综合**：AI 自动总结搜索结果，提取关键信息
- **引用追踪**：完整保留所有引用来源，确保信息可追溯

---

## 系统架构

### 多提供商 AI 模型系统
- **负载均衡**：支持多个 API 密钥的加权随机选择
- **速率限制**：自动跟踪 API 调用次数，避免超限
- **时间路由**：00:30-08:30 优先使用 DeepSeek（低成本时段）
- **故障转移**：API 密钥失效时自动切换备用密钥

**支持的 AI 提供商**：
- DeepSeek
- SiliconFlow
- Aliyun (通过 New API)
- 其他兼容 OpenAI 格式的 API

### 任务管理系统
- **持久化存储**：所有任务保存到 `data/tasks.json`
- **后台执行**：使用线程池执行分析任务，不阻塞主进程
- **进度跟踪**：详细记录每个阶段的进度和状态
- **任务控制**：支持暂停、重启、停止操作
- **自动清理**：24 小时后自动清理未支付的过期任务

### Web 搜索流程
1. **决策阶段**：判断是否需要搜索（基于用户输入）
2. **查询生成**：AI 生成 1-3 个相关搜索查询
3. **执行搜索**：调用 Bocha API 获取结果
4. **内容综合**：AI 总结搜索结果
5. **引用展示**：仅在 UI 显示引用，完整数据存储到后端

---

## 系统要求

- **操作系统**：Linux / macOS / Windows
- **Python**：3.8+
- **网络**：需要访问 AI API 和 Web 搜索 API

---

## 配置

### 环境变量配置 (.env)

所有敏感配置通过环境变量管理，复制 `env_example.txt` 为 `.env` 并填入实际值：

```bash
# Flask 配置
FLASK_SECRET_KEY=your-secret-key-here
ADMIN_PASSWORD=your-admin-password

# Bocha 搜索 API
BOCHA_API_KEY=your-bocha-api-key

# 邮件配置 (QQ邮箱)
SMTP_SERVER=smtp.qq.com
SMTP_PORT=465
SENDER_EMAIL=your-email@qq.com
SENDER_PASSWORD=your-email-auth-code

# AI 模型 API (至少配置一个)
DEEPSEEK_API_KEY=your-deepseek-key
SILICONFLOW_API_KEY=your-siliconflow-key
NEW_API_KEY=your-custom-api-key
NEW_API_URL=http://your-api-server/v1/chat/completions
```

### AI 模型配置

模型配置文件位于 `models/{provider}/*.json`，使用 `${VAR_NAME}` 语法引用环境变量：

```json
{
  "model_name": {
    "api_keys": [
      {
        "api_url": "${DEEPSEEK_API_URL}",
        "api_key": "${DEEPSEEK_API_KEY}",
        "weight": 1,
        "rate_limit": 60,
        "status": "active"
      }
    ]
  }
}
```

**配置说明**：
- `weight`: API 密钥的权重（越大越容易被选中）
- `rate_limit`: 每分钟最大调用次数
- `status`: `active` 启用 / `inactive` 禁用

---

## 使用指南

### 第一步：产品描述优化

1. 点击"开始分析"
2. 描述你的产品（可以粗略描述）
3. AI 助手会通过对话逐步明确：
   - 目标用户是谁？
   - 解决什么问题？
   - 核心功能是什么？
   - 竞品情况如何？
4. AI 会自动搜索相关信息作为参考
5. 确认最终的【产品描述】后进入下一步

### 第二步：用户画像配置

1. 设置**用户画像数量**（建议 5-20 个）
2. 设置**每个画像的模拟次数**（建议 2-5 次）
3. 选择付费方式或使用邀请码
4. 提交任务

### 第三步：等待分析

系统会在后台：
1. 生成多样化的用户画像（约 30-60 秒/画像）
2. 模拟每个用户对产品的反应（约 20-40 秒/模拟）
3. 生成详细的 HTML 报告（约 10-20 秒）
4. 发送报告到邮箱（如果配置）

大型分析（如 20 画像 × 5 模拟）可能需要 10-20 分钟。

### 第四步：查看报告

报告包含：
- **数据概览**：刚需比例、依赖度分布图表
- **用户画像详情**：每个画像的详细信息和模拟反馈
- **参考资料**：所有 Web 搜索引用来源（底部）

---

## 付费与 VIP

### 免费额度
- **快速尝鲜**：2 个画像 × 2 次模拟 = 免费

### 付费规则
- 总人数 = 画像数量 × 模拟次数
- 示例：10 画像 × 3 模拟 = 30 人次
- 定价请联系管理员

### VIP 特权
- 无限制使用
- 优先处理
- VIP 账号存储在 `data/accountsData/`

### 邀请码
- 使用有效邀请码可免费分析 10 个画像
- 邀请码记录在 `data/inviteData/`

---

## 管理功能

### 管理面板

访问：`http://localhost:5001/admin/tasks?key=admin123`

**功能**：
- 查看所有任务状态
- 停止运行中的任务
- 重启失败的任务
- 强制启动待支付任务
- 下载原始数据文件（画像、模拟、报告）

### API 端点

```bash
# 停止任务
POST /api/task/<task_id>/stop?key=admin123

# 重启任务
POST /api/task/<task_id>/restart?key=admin123

# 启动待支付任务
POST /api/task/<task_id>/start?key=admin123

# 下载文件
GET /admin/tasks/<task_id>/download/<file_type>?key=admin123
```

---

## 文件结构

```
polyscore/
├── app.py                          # Flask 主应用
├── setup.sh                        # 一键安装脚本（Linux）
├── requirements.txt                # Python 依赖
├── README_1213.md                  # 本文档
│
├── agent/                          # AI 代理模块
│   ├── __init__.py
│   ├── utils/
│   │   ├── runner.py              # 任务编排
│   │   ├── api_utils.py           # AI API 调用
│   │   ├── persona_generate.py    # 画像生成
│   │   ├── simulation_generate.py # 反应模拟
│   │   ├── report_generate.py     # 报告生成
│   │   ├── bocha_web_search.py    # Bocha API 集成
│   │   ├── web_search_pipeline.py # Web 搜索流程
│   │   ├── tasks.py               # 任务管理
│   │   └── email.py               # 邮件发送
│   └── prompt_template/
│       ├── prompt_zn.py           # 中文提示词
│       └── prompt_en.py           # 英文提示词
│
├── models/                         # AI 模型配置
│   ├── model_utils.py             # 模型池加载
│   ├── deepseek/
│   │   └── models.json
│   ├── siliconflow/
│   │   └── models.json
│   └── new_api_aliyun/
│       └── models.json
│
├── static/                         # 静态资源
│   ├── css/
│   ├── js/
│   └── images/
│
├── templates/                      # HTML 模板
│   ├── index.html                 # 首页
│   ├── step1.html                 # 产品描述页
│   ├── step2.html                 # 配置页
│   └── admin_tasks.html           # 管理页
│
├── data/                           # 数据存储
│   ├── tasks.json                 # 任务记录
│   ├── conversations/             # 对话历史
│   ├── accountsData/              # VIP 账户
│   ├── inviteData/                # 邀请码
│   ├── {task_id}_description.txt  # 产品描述
│   ├── {task_id}_personas.json    # 用户画像
│   ├── {task_id}_simulations.json # 模拟结果
│   └── {task_id}_web_search.json  # 搜索元数据
│
└── reports/                        # 生成的报告
    └── {task_id}_report.html
```

---

## 安全建议

### 生产环境必做

1. **修改密钥**（在 `.env` 文件中）：
   ```bash
   FLASK_SECRET_KEY=your-strong-secret-key
   ADMIN_PASSWORD=your-secure-admin-password
   ```

2. **确保 `.env` 不被提交**：
   - `.gitignore` 已包含 `.env` 规则
   - 切勿将 `.env` 文件提交到版本控制

3. **启用 HTTPS**：
   - 使用 Nginx 反向代理
   - 配置 SSL 证书（Let's Encrypt）

4. **限制访问**：
   - 使用防火墙限制管理接口访问
   - 配置 IP 白名单

5. **定期备份**：
   ```bash
   tar -czf backup_$(date +%Y%m%d).tar.gz data/ reports/
   ```

---

## 常见问题

### Q: 任务一直卡在 "运行中" 状态？
A:
1. 检查后端日志是否有错误
2. 使用管理面板停止并重启任务
3. 检查 AI API 密钥是否有效

### Q: Web 搜索没有结果？
A:
1. 确认 Bocha API 密钥配置正确
2. 检查网络连接
3. 查看 `agent/utils/bocha_web_search.py` 日志

### Q: 报告生成失败？
A:
1. 检查 `data/{task_id}_personas.json` 是否存在
2. 检查 `data/{task_id}_simulations.json` 是否完整
3. 查看 `agent/utils/report_generate.py` 错误信息

### Q: 如何修改定价？
A: 修改 `app.py` 中的 `calculate_price()` 函数。

---

## 性能优化

### 加速技巧
1. **使用 uv**：比 pip 快 10-100 倍
2. **增加 API 密钥**：提高并发能力
3. **调整 weight**：为高速 API 分配更高权重
4. **优化提示词**：减少 token 消耗

### 监控指标
- API 调用成功率
- 平均响应时间
- 任务完成时长
- 错误率


---

## 更新日志

### v1.1 (2025-12-23)
- ✅ 开源版本发布
- ✅ 敏感信息通过环境变量配置
- ✅ 添加 `env_example.txt` 配置模板
- ✅ 模型配置支持 `${VAR}` 环境变量语法

### v1.0 (2025-12-13)
- ✅ 集成 Bocha AI Web 搜索
- ✅ 多提供商 AI 模型负载均衡
- ✅ 用户画像多轮验证机制
- ✅ HTML 报告优化（参考资料置底）
- ✅ 任务管理系统重构
- ✅ 一键安装脚本（Linux）

---

## 许可证

MIT License - 详见 [LICENSE](LICENSE) 文件

---

## 致谢

- **大创项目 PolyScore Justin**
- [Flask](https://flask.palletsprojects.com/) - Web 框架
- [Chart.js](https://www.chartjs.org/) - 数据可视化
- [Bocha AI](https://bocha.ai/) - Web 搜索服务
- [uv](https://github.com/astral-sh/uv) - 极速包管理器
- [DeepSeek](https://deepseek.com/) - AI 模型提供商

---

**祝使用愉快！如有问题，欢迎提 Issue或联系邮箱roschild.rui@gmail.com 🎉**
