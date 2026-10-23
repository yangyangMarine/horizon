# 跨平台迁移操作指南 (Migration Guide)

本指南指导如何将 Horizon 系统从 Render 迁移至任何支持 Python 3.12+ 的云主机、本地设备或 Docker 环境。

## 迁移执行流程

### 第 1 步：从原环境导出知识与备份
在 Web 管理后台点击“打包导出便携专家包 (ZIP)”及“创建完整系统备份”，下载对应的两个 ZIP 归档。

### 第 2 步：在新环境准备代码库
```bash
git clone https://github.com/your-username/horizon.git
cd horizon
uv venv .venv
source .venv/bin/activate  # 或 Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 第 3 步：恢复数据与环境变量
1. 配置新环境的 `.env` 文件（设置 `GEMINI_API_KEY` 与 `ADMIN_PASSWORD`）。
2. 执行恢复脚本：
   ```bash
   python scripts/restore.py /path/to/downloaded_backup.zip
   ```
3. 重构检索索引：
   ```bash
   python scripts/build_index.py
   ```

### 第 4 步：验证完整性
运行单元测试，确认所有组件均在新环境中正常工作：
```bash
pytest -v
```
测试通过后即可通过 `streamlit run app.py` 启动服务。
