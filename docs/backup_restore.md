# 备份与灾难恢复指南 (Backup & Restore)

## 1. 专家知识包导出 vs 运维完整备份
- **专家知识包 (Expert Package)**：
  仅包含结构化宏观框架、主张、案例、预测及视频元数据。纯净无敏感凭证，体积轻巧，便于在不同设备、AI 模型间无缝流转。
  ```bash
  python scripts/export_package.py
  ```
  生成文件：`data/exports/horizon_expert_pack_YYYYMMDD_HHMMSS.zip`

- **运维完整备份 (Operational Backup)**：
  包含当前数据库快照（对话记录、用户表、转录分块）及专家知识包。
  ```bash
  python scripts/backup.py
  ```
  生成文件：`data/exports/horizon_backup_operational_YYYYMMDD_HHMMSS.zip`

## 2. 灾难恢复步骤 (Disaster Recovery)
在全新的机器或重置后的服务实例中执行恢复：
```bash
python scripts/restore.py data/exports/horizon_backup_operational_20260301_120000.zip
python scripts/build_index.py
```
恢复完成后，系统将自动校验数据库完整性并重建 FTS5 全文索引。
