"""
app.py
Horizon: Private, Portable AI Investment Expert Website
Main Streamlit application with secure session login, chat interface,
staged video ingestion, knowledge distillation, and package export.
"""

import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

from ingestion.pipeline import IngestPipeline
from src.macro_expert.auth import AuthManager
from src.macro_expert.citations import format_citations_markdown
from src.macro_expert.config import load_config
from src.macro_expert.conversations import ConversationManager
from src.macro_expert.cost_control import CostController
from src.macro_expert.database import Database
from src.macro_expert.expert import MacroExpertEngine
from src.macro_expert.export import ExportManager
from src.macro_expert.knowledge_package import KnowledgePackageManager
from src.macro_expert.llm import get_llm_adapter
from src.macro_expert.retrieval import HybridRetriever

# Page Setup
st.set_page_config(
    page_title="Horizon - 私人宏观投资AI专家",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom Styling
st.markdown("""
<style>
    .main-header {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
        color: #1E293B;
        font-weight: 700;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        color: #64748B;
        font-size: 0.95rem;
        margin-bottom: 1.5rem;
    }
    .metric-card {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 8px;
        padding: 1rem;
        text-align: center;
    }
    .citation-box {
        background-color: #F1F5F9;
        border-left: 4px solid #3B82F6;
        padding: 0.8rem;
        border-radius: 4px;
        margin-top: 0.8rem;
        font-size: 0.88rem;
    }
    .status-badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 12px;
        font-size: 0.75rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

# Application Context & Singletons
@st.cache_resource
def get_app_context():
    config = load_config()
    db = Database(config.storage.database_path)
    auth_mgr = AuthManager(
        db,
        max_attempts=config.security.max_login_attempts,
        lockout_minutes=config.security.lockout_minutes,
        session_timeout_minutes=config.security.session_timeout_minutes
    )
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "horizon_expert_2026")
    auth_mgr.ensure_admin_user(admin_user, admin_pass)

    pkg_mgr = KnowledgePackageManager(config.knowledge.package_path, db)
    # Ensure baseline data is loaded
    try:
        pkg_mgr.sync_to_database()
    except Exception as e:
        pass

    conv_mgr = ConversationManager(db)
    retriever = HybridRetriever(db, top_k=config.retrieval.top_k)
    llm = get_llm_adapter(config)
    cost_ctrl = CostController(db, config.limits)
    expert_engine = MacroExpertEngine(retriever, llm, cost_ctrl, config)
    export_mgr = ExportManager(config.knowledge.package_path, config.knowledge.export_path, db)
    pipeline = IngestPipeline(db, llm, config.knowledge.package_path)

    return {
        "config": config,
        "db": db,
        "auth_mgr": auth_mgr,
        "conv_mgr": conv_mgr,
        "retriever": retriever,
        "llm": llm,
        "cost_ctrl": cost_ctrl,
        "expert_engine": expert_engine,
        "export_mgr": export_mgr,
        "pipeline": pipeline,
        "pkg_mgr": pkg_mgr
    }

ctx = get_app_context()

# Session State Initialization
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

# ==============================================================================
# 1. Authentication View
# ==============================================================================
if not st.session_state.authenticated:
    st.markdown("<h1 class='main-header'>🧭 Horizon 宏观投资AI专家</h1>", unsafe_allow_html=True)
    st.markdown("<p class='sub-header'>私有化便携式投研决策中枢 · 视频知识蒸馏与因果推演系统</p>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1.8, 1])
    with col2:
        st.info("🔒 系统已启用私有化访问控制。请使用管理员授权凭证登录。")
        with st.form("login_form"):
            username = st.text_input("用户名 (Username)", value="admin")
            password = st.text_input("登录密码 (Password)", type="password")
            submit = st.form_submit_button("登录验证 (Sign In)")

            if submit:
                user = ctx["auth_mgr"].authenticate(username, password)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.success("登录成功！正在进入研报工作台...")
                    st.rerun()
                else:
                    st.error("用户名或密码错误，或由于多次尝试触发安全锁定。")
        st.caption("默认初始密码由环境变量 `ADMIN_PASSWORD` 配置。生产部署建议即刻更新。")
    st.stop()

# ==============================================================================
# 2. Authenticated Dashboard Layout
# ==============================================================================

# Sidebar: Conversations & Account
with st.sidebar:
    st.markdown("### 🧭 **Horizon 投研中枢**")
    st.caption(f"当前用户: `{st.session_state.username}`")

    if st.button("➕ 新建研判对话", use_container_width=True):
        new_id = ctx["conv_mgr"].create_conversation(title="新研判对话")
        st.session_state.current_conversation_id = new_id
        st.rerun()

    st.markdown("---")
    st.markdown("#### 📜 历史对话列表")

    convs = ctx["conv_mgr"].list_conversations()
    if not convs:
        # Create initial conversation if none exist
        init_id = ctx["conv_mgr"].create_conversation(title="初始宏观研判")
        st.session_state.current_conversation_id = init_id
        convs = ctx["conv_mgr"].list_conversations()

    if not st.session_state.current_conversation_id and convs:
        st.session_state.current_conversation_id = convs[0]["conversation_id"]

    for c in convs:
        cid = c["conversation_id"]
        title = c["title"][:16] + ("..." if len(c["title"]) > 16 else "")
        is_active = (cid == st.session_state.current_conversation_id)
        btn_label = f"📌 {title}" if is_active else f"💬 {title}"
        if st.button(btn_label, key=f"conv_btn_{cid}", use_container_width=True):
            st.session_state.current_conversation_id = cid
            st.rerun()

    st.markdown("---")
    # Quick management
    if st.session_state.current_conversation_id:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ 删除对话", use_container_width=True):
                ctx["conv_mgr"].delete_conversation(st.session_state.current_conversation_id)
                st.session_state.current_conversation_id = None
                st.rerun()
        with c2:
            export_md = ctx["conv_mgr"].export_conversation_markdown(st.session_state.current_conversation_id)
            st.download_button(
                "📥 导出记录",
                data=export_md,
                file_name=f"horizon_chat_{st.session_state.current_conversation_id}.md",
                mime="text/markdown",
                use_container_width=True
            )

    st.markdown("---")
    if st.button("🚪 退出登录", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.current_conversation_id = None
        st.rerun()

# Main Workspace Tabs
tab_chat, tab_ingest, tab_expert_pack, tab_usage = st.tabs([
    "💬 研判对话 (Chat & Reasoning)",
    "📥 视频知识收录 (Video Ingestion)",
    "📦 专家知识包管理 (Expert Pack)",
    "📊 监控与额度 (Cost & Usage)"
])

# ------------------------------------------------------------------------------
# TAB 1: Chat & Reasoning
# ------------------------------------------------------------------------------
with tab_chat:
    active_cid = st.session_state.current_conversation_id
    if active_cid:
        current_conv = ctx["conv_mgr"].get_conversation(active_cid)
        conv_title = current_conv["title"] if current_conv else "对话"
        st.subheader(f"📑 {conv_title}")

        # Display Chat History
        messages = ctx["conv_mgr"].get_messages(active_cid)
        for msg in messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.markdown(msg["content"])
            else:
                with st.chat_message("assistant", avatar="🧭"):
                    st.markdown(msg["content"])
                    if msg.get("citations"):
                        with st.expander("📚 查看本条回答的溯源证据与对应视频出处"):
                            for c in msg["citations"]:
                                cat = c.get("category", "")
                                title = c.get("title", "")
                                date = f" · 发布日期: {c.get('publish_date')}" if c.get('publish_date') else ""
                                ts = f" · 时间戳: {c.get('timestamp')}" if c.get('timestamp') else ""
                                st.markdown(f"**[{cat}] {title}**{date}{ts}")
                                if c.get("video_id"):
                                    url_part = f" · [点击查看原视频]({c.get('video_url')})" if c.get("video_url") else ""
                                    st.caption(f"视频ID: `{c.get('video_id')}`{url_part} · 校验状态: `{c.get('verification_status')}`")
                                if c.get("verbatim_quote"):
                                    st.markdown(f"> *\"{c.get('verbatim_quote')}\"*")
                                st.markdown("---")

        # Chat Input
        user_prompt = st.chat_input("向 Horizon 专家提出宏观经济、债券收益率、流动性或市场传导问题...")
        if user_prompt:
            # 1. Display user query
            with st.chat_message("user"):
                st.markdown(user_prompt)

            # Update conversation title if first message
            if len(messages) == 0:
                short_title = user_prompt[:18] + ("..." if len(user_prompt) > 18 else "")
                ctx["conv_mgr"].update_title(active_cid, short_title)

            # Save user message
            ctx["conv_mgr"].add_message(active_cid, "user", user_prompt)

            # 2. Generate response with Expert Engine
            with st.chat_message("assistant", avatar="🧭"):
                with st.spinner("Horizon 正在检索创作者核心分析框架并进行因果推演..."):
                    resp = ctx["expert_engine"].answer_question(user_prompt)

                    # Append formatted citations to markdown
                    citations_md = format_citations_markdown(resp.citations)
                    full_answer = resp.answer_text + citations_md
                    st.markdown(full_answer)

                    # Save assistant message
                    ctx["conv_mgr"].add_message(
                        conversation_id=active_cid,
                        role="assistant",
                        content=resp.answer_text,
                        model_name=resp.model_name,
                        citations=[c.model_dump() for c in resp.citations],
                        tokens_used=resp.tokens_used
                    )
            st.rerun()

# ------------------------------------------------------------------------------
# TAB 2: Video Ingestion & 1-Click Update
# ------------------------------------------------------------------------------
with tab_ingest:
    st.subheader("📥 创作者新视频收录与一键知识蒸馏")
    st.markdown(
        "当创作者在抖音发布新视频时，在此直接输入视频链接或上传音视频材料，"
        "系统将自动完成 **多模态转录 ➔ 术语清洗 ➔ 语义分块 ➔ 原子主张提炼 ➔ 检索索引同步** 全流程。"
    )

    with st.expander("✨ 录入并一键更新知识库 (Add New Video)", expanded=True):
        col_url, col_title = st.columns([2, 2])
        with col_url:
            in_url = st.text_input("抖音视频网页链接 (Video URL)", placeholder="https://www.douyin.com/video/7220000000000000001")
        with col_title:
            in_title = st.text_input("视频标题 (Title)", placeholder="例如：美债收益率与财政赤字分析")

        in_date = st.date_input("发布日期 (Publish Date)")
        
        st.markdown("**资料输入方式 (二选一或结合使用):**")
        method_tab1, method_tab2 = st.tabs(["📝 粘贴视频文本/转录稿 (Fast Text)", "🎵 上传音视频文件 (Audio/Video File)"])
        
        in_transcript = None
        in_media_file = None
        
        with method_tab1:
            in_transcript = st.text_area(
                "粘贴视频转录稿文本 (可包含创作者发言内容)",
                placeholder="创作者在视频中说道：当美债供给放量，一级交易商承接力有限，买家只能要求更高的期限溢价...",
                height=150
            )
        with method_tab2:
            in_media_file = st.file_uploader("上传音视频文件 (支持 mp4, mp3, wav, m4a)", type=["mp4", "mp3", "wav", "m4a"])

        if st.button("🚀 一键提炼并同步知识库 (1-Click Extract & Sync)", type="primary"):
            if not in_url or not in_title:
                st.error("请至少填写视频链接与视频标题。")
            else:
                with st.spinner("正在执行知识蒸馏流水线，请稍候..."):
                    media_path = None
                    if in_media_file:
                        temp_save = Path("./data/audio") / in_media_file.name
                        temp_save.parent.mkdir(parents=True, exist_ok=True)
                        with open(temp_save, "wb") as f:
                            f.write(in_media_file.getbuffer())
                        media_path = temp_save

                    res = ctx["pipeline"].process_new_video(
                        url=in_url,
                        title=in_title,
                        media_path=media_path,
                        transcript_text=in_transcript if in_transcript and in_transcript.strip() else None,
                        publish_date=str(in_date)
                    )

                    if res.get("status") == "success":
                        st.success(res["message"])
                        st.balloons()
                    else:
                        st.info(res.get("message", "处理完成。"))

    st.markdown("---")
    st.markdown("#### 📋 已收录视频库清单 (Video Inventory)")
    with ctx["db"].session() as conn:
        cur = conn.execute("SELECT video_id, title, publish_date, ingestion_status, review_status FROM videos ORDER BY publish_date DESC;")
        videos = cur.fetchall()

    if videos:
        table_data = [dict(v) for v in videos]
        st.dataframe(table_data, use_container_width=True)
    else:
        st.info("当前尚未收录视频记录。")

# ------------------------------------------------------------------------------
# TAB 3: Expert Pack Management & Portable Export
# ------------------------------------------------------------------------------
with tab_expert_pack:
    st.subheader("📦 专家知识包 (Portable Expert Package)")
    st.markdown(
        "Horizon 的核心架构原则是：**将专家知识资产与应用平台解耦**。"
        "知识包由纯文本 Markdown、JSONL 和 YAML 清单构成，可独立迁移至任何本地模型或云环境。"
    )

    manifest = ctx["pkg_mgr"].load_manifest()
    inv = manifest.get("inventory", {})

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("核心框架 (Frameworks)", inv.get("frameworks", 0))
    with c2:
        st.metric("原子主张 (Atomic Claims)", inv.get("claims", 0))
    with c3:
        st.metric("收录视频 (Sources)", inv.get("sources", 0))
    with c4:
        st.metric("历史案例 (Cases)", inv.get("cases", 0))

    st.markdown("---")
    col_rebuild, col_export_pack, col_export_backup = st.columns(3)

    with col_rebuild:
        if st.button("🔄 重新同步并重建 FTS 索引", use_container_width=True):
            with st.spinner("正在校验清单并重构索引..."):
                counts = ctx["pkg_mgr"].sync_to_database()
                st.success(f"索引重构完成！共索引 {counts.get('fts_indexed', 0)} 条知识记录。")

    with col_export_pack:
        if st.button("📦 打包导出便携专家包 (ZIP)", use_container_width=True):
            zip_p = ctx["export_mgr"].export_expert_package_zip()
            with open(zip_p, "rb") as f:
                st.download_button(
                    "⬇️ 点击下载专家知识包 ZIP",
                    data=f.read(),
                    file_name=zip_p.name,
                    mime="application/zip",
                    use_container_width=True
                )

    with col_export_backup:
        if st.button("💾 创建完整系统备份 (Full Backup)", use_container_width=True):
            bak_p = ctx["export_mgr"].create_operational_backup_zip()
            with open(bak_p, "rb") as f:
                st.download_button(
                    "⬇️ 点击下载完整备份 ZIP",
                    data=f.read(),
                    file_name=bak_p.name,
                    mime="application/zip",
                    use_container_width=True
                )

# ------------------------------------------------------------------------------
# TAB 4: Cost & Guardrails Monitoring
# ------------------------------------------------------------------------------
with tab_usage:
    st.subheader("📊 预算、Token 与调用监控 (Cost Management)")
    usage = ctx["cost_ctrl"].get_usage_summary()

    m1, m2, m3, m4 = st.columns(4)
    with m1:
        st.metric("今日请求量", f"{usage['today_requests']} 次", f"上限 {ctx['config'].limits.daily_request_limit}")
    with m2:
        st.metric("今日估算费用", f"${usage['today_cost_usd']:.4f}")
    with m3:
        st.metric("本月总消耗 Token", f"{usage['monthly_tokens']:,}")
    with m4:
        st.metric("本月累计费用", f"${usage['monthly_cost_usd']:.4f}", f"限额 ${usage['monthly_budget_usd']:.2f}")

    st.markdown("---")
    st.markdown("#### 🔒 安全与调用防护策略")
    st.markdown(f"""
    - **单次提问长度限制**: `{ctx['config'].limits.max_question_characters}` 字符
    - **模型调用超时**: `{ctx['config'].llm.timeout_seconds}` 秒
    - **当前核心模型**: `{ctx['config'].llm.model}` (Gemini API)
    - **多级溯源审查**: 创作者原话 / 创作者框架 / AI 推演 / 外部事实
    """)
