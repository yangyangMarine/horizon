# 知识包数据架构规范 (Knowledge Schema Specification)

专家知识包存储在 `expert_pack/` 目录中，格式为纯文本 Markdown、JSONL 与 YAML。

## 1. 结构与文件清单
```
expert_pack/
├── manifest.yaml           # 包版本、元数据清单与 SHA-256 校验和
├── README.md               # 知识包说明
├── identity.md             # 专家人格与领域能力定义
├── reasoning_rules.md      # 因果传导与证伪推演准则
├── answer_policy.md        # 四级溯源与回答合规规范
├── frameworks/             # 核心主题框架 (Markdown)
│   ├── monetary_policy.md  # 货币政策时滞与再融资墙模型
│   ├── sovereign_debt.md   # 主权债务与期限溢价利息螺旋
│   └── liquidity.md        # 美联储净流动性方程
├── claims/
│   └── claims.jsonl        # 原子主张 (包含机制、触发条件、时间戳)
├── cases/
│   └── cases.jsonl         # 历史危机对比案例
├── forecasts/
│   └── forecasts.jsonl     # 创作者历史确切预测记录 (不可篡改)
├── sources/
│   └── source_catalog.jsonl# 收录视频源目录
└── evaluation/
    └── test_questions.jsonl# 评测基准题库
```

## 2. 原子主张 (Atomic Claim) Schema
```json
{
  "claim_id": "clm_001",
  "video_id": "vid_macro_2023_09_15",
  "source_segment_ids": ["seg_003"],
  "topic": "sovereign_debt",
  "subtopic": "term_premium",
  "claim_text": "美债发债规模井喷直接推升期限溢价，导致10年期美债收益率冲高。",
  "claim_type": "causal_mechanism",
  "mechanism": "财政部海量发债导致一级交易商承接能力达到瓶颈，买方要求更高的期限风险补偿。",
  "conditions": "私人部门与海外官方买盘未能同步大幅扩容。",
  "indicators": "ACM期限溢价模型、美债拍卖投标倍数。",
  "assets_affected": ["10年期美债", "纳斯达克科技股"],
  "time_horizon": "medium_term",
  "confidence_expression": "high",
  "evidence_text": "当财政部三季度借款预估大幅超预期...",
  "timestamp_range": "02:15 - 03:02",
  "review_status": "verified"
}
```
