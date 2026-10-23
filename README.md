# Horizon: 私人便携式宏观投资AI专家与视频知识蒸馏系统
### Private, Portable AI Investment Expert Website with Video Knowledge Distillation

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Streamlit](https://img.shields.io/badge/UI-Streamlit-red.svg)](https://streamlit.io/)
[![Gemini](https://img.shields.io/badge/AI-Google%20Gemini-orange.svg)](https://ai.google.dev/)
[![Tests](https://img.shields.io/badge/Tests-14%20Passed-brightgreen.svg)](tests/)

---

## 1. 核心定位与设计哲学

**Horizon** 专为个人深度投研打造。系统通过学习特定宏观经济与投资创作者的数百期视频内容，提炼出结构化的因果逻辑、机制模型与历史案例，将其转化为高可迁移性、防幻觉、带确凿时间戳证据链的私人投研决策助手。

### 核心特性
- **专家资产与平台彻底解耦**：知识包以 Markdown + JSONL + YAML 形式独立存在（`expert_pack/`），不依赖任何特定云厂商或向量库，可一键打包迁移。
- **Gemini 多模态深度赋能**：利用 Google Gemini API 官方 SDK（`google-genai`），原生支持中文金融音视频多模态转录、术语自动清洗、长上下文因果推演与结构化主张抽取。
- **严谨的四级溯源与防幻觉机制**：
  1. `【创作者原话】`：精确锁定原视频、发布日期、时间戳与原文字句；
  2. `【创作者框架】`：综合多期视频沉淀的传导模型与因果链；
  3. `【AI 推演】`：针对全新宏观情境，明确标识为 AI 独立演绎，绝不冒充创作者原意；
  4. `【外部事实】`：标明数据来源与观测日期。
- **创作者新视频一键更新**：提供极简的 Web 界面一键收录与后台命令行批量流水线，自动完成多模态转录、分块、提炼并实时更新检索索引。
- **开箱即用的私有化安全控制**：Bcrypt 加盐哈希认证、防暴力破解锁定机制、Token 成本预算告警与完整灾难恢复保障。

---

## 2. 快速上手指南 (Quick Start)

### 环境要求
- Python 3.12+ (或使用 `uv` / Anaconda)
- Google Gemini API 密钥

---

### 方式 A: 使用 `uv` (推荐，极速安装)
```bash
# 1. 克隆代码仓库并进入项目根目录
cd c:\Users\yyang29\Documents\Github\horizon

# 2. 创建虚拟环境并安装依赖
uv venv .venv
.venv\Scripts\activate          # Windows
# source .venv/bin/activate     # Linux/macOS
uv pip install -r requirements.txt

# 3. 配置环境变量
copy .env.example .env          # Windows
# cp .env.example .env          # Linux/macOS
```
在 `.env` 中填入您的 `GEMINI_API_KEY` 及自定义管理员密码：
```ini
GEMINI_API_KEY=AIzaSy...
ADMIN_PASSWORD=YourSecurePassword123!
```

---

### 方式 B: 使用 Anaconda / Conda
```bash
# 1. 创建并激活 Python 3.12 虚拟环境
conda create -n horizon python=3.12 -y
conda activate horizon

# 2. 安装项目依赖
pip install -r requirements.txt

# 3. 复制并编辑环境变量
copy .env.example .env
```

---

### 初始化数据库与全文索引
```bash
python scripts/build_index.py
```
*(将自动载入 `expert_pack` 内的核心框架、主张、案例与基准预测，并构建 SQLite FTS5 检索引擎)*

---

### 启动 Horizon Web 工作台
```bash
streamlit run app.py
```
在浏览器中打开提示的本地地址（默认 `http://localhost:8501`），输入账号 `admin` 及您设定的密码即可进入。

---

## 3. 当创作者发布新视频时：如何更新知识库？

Horizon 专为视频更新设计了两种简易工作流：

### 方式 1：Web 界面一键收录 (UI 1-Click Update)
1. 登录 Horizon，切换到顶部导航栏的 **“📥 视频知识收录 (Video Ingestion)”** 选项卡。
2. 粘贴新视频的抖音链接与视频标题。
3. **二选一或同时提供**：
   - **文字稿**：在“粘贴视频文本/转录稿”中粘贴视频核心文字；
   - **音视频**：在“上传音视频文件”中直接上传 `.mp4`、`.mp3` 或 `.m4a` 录音文件。
4. 点击 **“🚀 一键提炼并同步知识库 (1-Click Extract & Sync)”**。
5. 系统将自动执行：**音频校验 ➔ Gemini 转录 ➔ 术语清洗 ➔ 语义分块 ➔ 原子主张提炼 ➔ FTS5 索引热更新**，并在对话页即刻生效！

### 方式 2：批量自动化脚本 (CLI Batch Update)
将新视频信息整理为 JSON 格式文件（例如 `data/new_videos.json`）：
```json
[
  {
    "url": "https://www.douyin.com/video/7330000000000000001",
    "title": "美债发债洪峰与银行流动性冲击",
    "transcript": "./data/transcripts/sample1.txt",
    "publish_date": "2026-03-01"
  }
]
```
运行批量处理工具：
```bash
python scripts/import_videos.py --batch data/new_videos.json
```

---

## 4. 自动化测试与质量评测

本项目包含 14 项端到端单元与集成测试（覆盖认证、防爆破、数据库、持久化对话、混合检索、溯源引证、知识包往返打包校验、成本额度保护、专家推理引擎与自动化流水线）：

```bash
pytest -v
```

所有测试均配置了确定性 `MockLLMAdapter`，**无需联网或消耗任何真实 API Token 即可在本地完整通过验证**。

---

## 5. 专家资产打包、备份与灾难恢复

### 导出便携专家知识包 (Expert Package ZIP)
生成可在任何环境迁移的轻量知识归档（包含 SHA-256 完整性清单）：
```bash
python scripts/export_package.py
```
导出路径：`data/exports/horizon_expert_pack_YYYYMMDD_HHMMSS.zip`

### 创建系统运维完整备份 (Full Backup)
安全快照当前 SQLite 数据库（包含对话历史、用户状态）及知识资产：
```bash
python scripts/backup.py
```

### 一键恢复系统 (Restore)
```bash
python scripts/restore.py data/exports/horizon_backup_operational_XXXX.zip
python scripts/build_index.py
```

---

## 6. 云端生产环境部署 (Render)

本项目已开箱支持 Render Web Service 云端部署：

1. 将代码推送到您的私有 GitHub 仓库；
2. 在 [Render Dashboard](https://render.com) 点击 **New +** ➔ **Blueprint** 并连接此仓库；
3. Render 将自动解析 `deployment/render.yaml`：
   - 自动绑定持久化存储盘到 `/opt/render/project/src/data`，确保对话记录与上传数据永不丢失；
   - 提示填写密钥环境变量 `GEMINI_API_KEY` 与 `ADMIN_PASSWORD`；
4. 点击 **Apply** 即可获得私有的 HTTPS 在线投资专家网站。

详细步骤与 Docker 部署说明请参考文档：[`deployment/deployment.md`](deployment/deployment.md)。

---

## 7. 目录结构概览

```
horizon/
├── app.py                      # Horizon 核心 Streamlit Web 应用
├── config.yaml                 # 平台配置与限额策略
├── .env.example                # 环境变量模版
├── requirements.txt            # 依赖清单
├── pyproject.toml              # 项目定义与 Pytest 配置
│
├── src/macro_expert/           # 核心业务与领域模型
│   ├── auth.py                 # 加盐哈希与登录防爆破
│   ├── citations.py            # 四级溯源与时间戳引证格式化
│   ├── config.py               # 强类型配置加载器
│   ├── conversations.py        # 历史对话与消息 CRUD
│   ├── cost_control.py         # Token 消耗与月度预算监控
│   ├── database.py             # SQLite 架构与 FTS5 全文索引
│   ├── expert.py               # 专家推理引擎 (Layer B)
│   ├── export.py               # ZIP 打包与备份恢复引擎
│   ├── knowledge_package.py    # 专家包加载与数据库同步
│   ├── llm.py                  # Gemini 官方 SDK 适配器与 Mock
│   ├── models.py               # Pydantic 领域模型
│   └── retrieval.py            # 混合检索引擎 (FTS5 + 中文 N-Gram)
│
├── ingestion/                  # 知识收录与蒸馏流水线
│   ├── audio_import.py         # 音视频文件去重与校验
│   ├── chunking.py             # 语义分块与时间窗口保留
│   ├── extraction.py           # 原子主张与因果机制抽取
│   ├── framework_builder.py    # 主题分析框架合成
│   ├── metadata_import.py      # 抖音链接解析与去重登记
│   ├── pipeline.py             # 一键自动化收录流水线
│   ├── transcript_cleaning.py  # 宏观金融术语标准化清洗
│   └── transcription.py        # Gemini 多模态语音转录适配器
│
├── expert_pack/                # 便携式专家知识包 (Layer A)
│   ├── manifest.yaml           # 包版本与 SHA-256 校验和
│   ├── identity.md             # 专家人格与领域能力定义
│   ├── reasoning_rules.md      # 因果传导与证伪推演准则
│   ├── answer_policy.md        # 四级溯源与回答合规规范
│   ├── frameworks/             # 核心宏观分析框架 (Markdown)
│   ├── claims/                 # 原子主张 (JSONL)
│   ├── cases/                  # 历史危机对比案例 (JSONL)
│   ├── forecasts/              # 历史确切预测记录 (JSONL)
│   ├── sources/                # 视频源目录 (JSONL)
│   └── evaluation/             # 50 项评测基准题库 (JSONL)
│
├── scripts/                    # 运维与批处理脚本
│   ├── build_index.py          # 重建检索索引
│   ├── import_videos.py        # 批量导入视频
│   ├── export_package.py       # 导出知识包
│   ├── backup.py / restore.py  # 备份与恢复
│   └── validate_package.py     # 校验知识包完整性
│
├── deployment/                 # 部署配置 (Render & Docker)
├── docs/                       # 架构、安全与运维详尽文档
└── tests/                      # 自动化单元与集成测试套件
```

---

## 8. 免责声明 (Disclaimer)

Horizon 系统仅供个人学术研究、宏观经济分析与模型推演学习使用。本系统输出的任何推导结论、推演模型及观点引用均不构成针对具体股票、债券、外汇或衍生品的买卖建议与投资决策依据。市场有风险，投资需独立审慎研判。
