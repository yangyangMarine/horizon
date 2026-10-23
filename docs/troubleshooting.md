# 故障排查与诊断指南 (Troubleshooting)

## 常见问题排查清单

### 1. 登录界面提示“用户名或密码错误，或触发安全锁定”
- **原因**：输错密码超过 5 次触发了 IP 级安全防爆破锁定。
- **解决方案**：
  等待 15 分钟锁定解除，或进入服务器重置管理员密码：
  ```bash
  python -c "from src.macro_expert.database import Database; from src.macro_expert.auth import AuthManager; db=Database('./data/app.db'); AuthManager(db).change_password('admin', 'new_password_123')"
  ```

### 2. 检索不到最近导入的视频内容
- **原因**：导入视频后尚未执行全文索引重构。
- **解决方案**：
  在 Web 控制台点击“重新同步并重建 FTS 索引”，或运行：
  ```bash
  python scripts/build_index.py
  ```

### 3. 未配置 Gemini API 密钥时提问
- **现象**：系统自动启用 `MockLLMAdapter` 返回标准研报示例。
- **解决方案**：
  在 `.env` 中填入合法的 `GEMINI_API_KEY=AIzaSy...` 并重启应用。

### 4. 音视频转录超时或网络波动
- **解决方案**：
  针对时长超过 15 分钟的长视频，建议将视频先分段或直接在 Web 界面“文本转录稿”输入框中粘贴文字内容，系统将自动进行语义切分与主张提炼。
