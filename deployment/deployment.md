# Horizon 生产环境部署指南 (Deployment Guide)

## 1. Render 云端一键部署 (推荐)

Render 提供便捷的 Python Web Service 部署及持久化硬盘 (Persistent Disk) 支持。

### 部署步骤：
1. **创建私有 GitHub 代码仓库**并推送本项目代码：
   ```bash
   git init
   git add .
   git commit -m "feat: initial release of horizon expert"
   git remote add origin https://github.com/your-username/horizon.git
   git push -u origin main
   ```
2. 登录 [Render.com](https://render.com)，点击 **New +** ➔ **Blueprint**，选择该私有仓库。
3. Render 会自动读取 `deployment/render.yaml`，并提示配置以下保密环境变量：
   - `GEMINI_API_KEY`: 您的 Google Gemini API 密钥
   - `ADMIN_PASSWORD`: 管理员私有登录密码（请设置高强度复杂密码）
4. **验证挂载存储**：
   - 确认持久化存储盘已正确挂载到 `/opt/render/project/src/data`，确保对话记录 `app.db`、音频缓存及备份不随容器重启丢失。
5. 点击 **Apply** 开始构建。构建完成后，Render 会分配专属 HTTPS 域名（例如 `https://horizon-macro-expert.onrender.com`）。

---

## 2. 本地与私有 VPS Docker 部署

如需在本地家庭服务器或私有 Linux VPS (Ubuntu/Debian) 上部署：

```bash
# 1. 复制并编辑环境变量
cp .env.example .env
nano .env

# 2. 构建镜像
docker build -t horizon-expert -f deployment/Dockerfile .

# 3. 运行容器并挂载数据卷
docker run -d \
  --name horizon \
  -p 8501:8501 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  --restart unless-stopped \
  horizon-expert
```
访问 `http://localhost:8501` 即可体验。
