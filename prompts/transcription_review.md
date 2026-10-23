# Transcription Review & Terminology Cleaning Prompt

Clean and normalize raw speech-to-text transcript segments from Chinese financial and investment videos.

## Financial Terminology Normalization Rules:
1. Ensure standard macroeconomic terminology (e.g., "缩表", "降息", "流动性陷阱", "美债收益率曲线倒挂", "期限溢价", "信用利差", "再通胀").
2. Standardize currency and units (e.g., "基点/bp", "万亿美元", "点位").
3. Preserve spoken nuances and hesitations without altering factual meaning.
4. If a word or number is ambiguous, flag it with `[uncertain: ...]` rather than guessing.
5. Retain original segment timestamps strictly.
