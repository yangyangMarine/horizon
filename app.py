"""
app.py
Horizon: Minimalist, Public-Facing AI Investment Expert Platform (ChatGPT / Gemini Style)
Features multi-expert knowledge base selector (e.g. Horizon Macro, Aili Investor),
sleek distraction-free chat UI, conversation history, and hidden admin controls.
"""

import os
import uuid
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

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

# ------------------------------------------------------------------------------
# 1. Page Configuration & Chrome Suppression (Hide Deploy/Manage/GitHub buttons)
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Horizon - AI 投资决策专家",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Strict CSS to hide all Streamlit management chrome, GitHub fork links, and default headers
st.markdown("""
<style>
    /* Hide Streamlit Header, Footer, and Toolbar */
    #MainMenu {visibility: hidden !important; display: none !important;}
    header[data-testid="stHeader"] {visibility: hidden !important; display: none !important;}
    footer {visibility: hidden !important; display: none !important;}
    .stDeployButton {display: none !important;}
    div[data-testid="stDecoration"] {display: none !important;}
    div[data-testid="stStatusWidget"] {visibility: hidden !important; display: none !important;}
    div[data-testid="stToolbar"] {display: none !important;}
    
    /* Hide Streamlit Cloud 'Manage app' and badge elements */
    iframe[title="manage-app"] {display: none !important;}
    [data-testid="manage-app-button"] {display: none !important;}
    .viewerBadge_container__1QSob {display: none !important;}
    .styles_viewerBadge__1yB5_ {display: none !important;}
    button[title="View app in Streamlit Community Cloud"] {display: none !important;}

    /* Modern Minimalist Chat Styling */
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 5rem;
        max-width: 900px;
    }
    
    /* Welcome Hero Card */
    .hero-card {
        text-align: center;
        padding: 3rem 1.5rem;
        margin-top: 2rem;
        margin-bottom: 2rem;
    }
    .hero-avatar {
        font-size: 3.5rem;
        margin-bottom: 0.8rem;
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 700;
        color: #1E293B;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1.05rem;
        color: #64748B;
        max-width: 620px;
        margin: 0 auto 2rem auto;
        line-height: 1.6;
    }
    
    /* Prompt Suggestion Card */
    .suggestion-btn {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        border-radius: 12px;
        padding: 1rem;
        text-align: left;
        color: #334155;
        font-size: 0.92rem;
        transition: all 0.2s ease;
        margin-bottom: 0.6rem;
    }
    .suggestion-btn:hover {
        border-color: #3B82F6;
        background-color: #EFF6FF;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. Experts & Knowledge Bases Registry
# ------------------------------------------------------------------------------
EXPERTS_REGISTRY = {
    "horizon_macro": {
        "id": "horizon_macro",
        "name": "Horizon 宏观策略专家 (默认)",
        "avatar": "🧭",
        "badge": "宏观流动性 · 美债收益率 · 周期演进",
        "description": "基于数百期宏观研判视频，精通美联储净流动性、主权债务利息螺旋与长端收益率因果推演。",
        "prompt_file": "analyst.md",
        "topic_filter": None,
        "sample_prompts": [
            "美法国债长端收益率走高，是否会重演欧债危机？",
            "美联储总资产减TGA减逆回购，这个净流动性公式如何指导美股？",
            "当美债利息支出占财政收入超过15%时，会触发什么传导机制？",
            "美国经济在2023-2024年为何没有出现预期的硬衰退？"
        ]
    },
    "aili": {
        "id": "aili",
        "name": "Aili (艾莉) 投资研判专家",
        "avatar": "👩‍💼",
        "badge": "商业壁垒 · 消费与科技 · 估值安全边际",
        "description": "基于博主 Aili 视频蒸馏，专注于产业生命周期S曲线、轻资产高ROE、自由现金流折现与逆向建仓逻辑。",
        "prompt_file": "aili_analyst.md",
        "topic_filter": "aili",
        "sample_prompts": [
            "Aili 博主如何评估一家高成长公司的估值安全边际？",
            "在行业下行周期中，Aili 认为应该关注哪些能够‘剩者为王’的核心指标？",
            "当市场情绪极度悲观时，Aili 的左侧逆向建仓逻辑是什么？",
            "轻资产高ROE公司与重资产周期股在抗通胀能力上有何本质区别？"
        ]
    },
    "liquidity_quant": {
        "id": "liquidity_quant",
        "name": "全球流动性与汇率智囊",
        "avatar": "🌊",
        "badge": "央行资负表 · 隔夜逆回购 · 黄金与美元",
        "description": "专注于全球美元潮汐、隔夜逆回购(ON RRP)、财政部发债计划与黄金大宗商品的传导机制。",
        "prompt_file": "analyst.md",
        "topic_filter": "liquidity",
        "sample_prompts": [
            "如果美联储逆回购资金池耗尽，发债将对商业银行准备金产生什么冲击？",
            "美元指数与黄金在中长期走势中如何打破传统负相关？",
            "央行降息初期往往出现资产价格震荡回调的机理是什么？"
        ]
    }
}

# ------------------------------------------------------------------------------
# 3. Context & Singletons
# ------------------------------------------------------------------------------
@st.cache_resource
def get_app_context():
    config = load_config()
    db = Database(config.storage.database_path)
    auth_mgr = AuthManager(db)
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "horizon_expert_2026")
    auth_mgr.ensure_admin_user(admin_user, admin_pass)

    pkg_mgr = KnowledgePackageManager(config.knowledge.package_path, db)
    try:
        pkg_mgr.sync_to_database()
    except Exception:
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

# ------------------------------------------------------------------------------
# 4. Session State & Visitor Isolation
# ------------------------------------------------------------------------------
if "visitor_user_id" not in st.session_state:
    st.session_state.visitor_user_id = f"user_{uuid.uuid4().hex[:8]}"

if "selected_expert_id" not in st.session_state:
    st.session_state.selected_expert_id = "horizon_macro"

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

selected_expert = EXPERTS_REGISTRY.get(st.session_state.selected_expert_id, EXPERTS_REGISTRY["horizon_macro"])

# ------------------------------------------------------------------------------
# 5. Left Sidebar (ChatGPT / Gemini Style)
# ------------------------------------------------------------------------------
with st.sidebar:
    # New Chat Pill
    if st.button("➕ 新建对话", use_container_width=True, type="primary"):
        new_cid = ctx["conv_mgr"].create_conversation(
            title="新对话",
            user_id=st.session_state.visitor_user_id
        )
        st.session_state.current_conversation_id = new_cid
        st.rerun()

    st.markdown("---")
    st.caption("🕒 **历史对话 (Recent Chats)**")

    user_convs = ctx["conv_mgr"].list_conversations(user_id=st.session_state.visitor_user_id)
    if not user_convs:
        # Create initial conversation
        init_cid = ctx["conv_mgr"].create_conversation(
            title="新研判对话",
            user_id=st.session_state.visitor_user_id
        )
        st.session_state.current_conversation_id = init_cid
        user_convs = ctx["conv_mgr"].list_conversations(user_id=st.session_state.visitor_user_id)

    if not st.session_state.current_conversation_id and user_convs:
        st.session_state.current_conversation_id = user_convs[0]["conversation_id"]

    for c in user_convs:
        cid = c["conversation_id"]
        title = c["title"][:14] + ("..." if len(c["title"]) > 14 else "")
        is_active = (cid == st.session_state.current_conversation_id)
        btn_label = f"💬 **{title}**" if is_active else f"💬 {title}"
        if st.button(btn_label, key=f"conv_{cid}", use_container_width=True):
            st.session_state.current_conversation_id = cid
            st.rerun()

    st.markdown("---")
    if st.session_state.current_conversation_id:
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🗑️ 清除此对话", use_container_width=True):
                ctx["conv_mgr"].delete_conversation(st.session_state.current_conversation_id)
                st.session_state.current_conversation_id = None
                st.rerun()
        with c2:
            export_md = ctx["conv_mgr"].export_conversation_markdown(st.session_state.current_conversation_id)
            st.download_button(
                "📥 导出记录",
                data=export_md,
                file_name=f"chat_{st.session_state.current_conversation_id}.md",
                mime="text/markdown",
                use_container_width=True
            )

    # Discreet Admin Access (Hidden in bottom expander for owner only)
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    with st.expander("⚙️ 知识库管理后台 (Admin Only)", expanded=False):
        if not st.session_state.admin_authenticated:
            admin_pwd = st.text_input("管理员密码", type="password", key="admin_pwd_input")
            if st.button("验证登录", key="admin_login_btn", use_container_width=True):
                user = ctx["auth_mgr"].authenticate("admin", admin_pwd)
                if user:
                    st.session_state.admin_authenticated = True
                    st.success("管理员权限已解锁")
                    st.rerun()
                else:
                    st.error("密码错误")
        else:
            st.success("已登录管理员权限")
            if st.button("退出管理模式", use_container_width=True):
                st.session_state.admin_authenticated = False
                st.rerun()

            st.markdown("---")
            st.markdown("**视频收录 & 知识蒸馏流水线**")
            adm_url = st.text_input("抖音视频链接", key="adm_v_url")
            adm_title = st.text_input("视频标题", key="adm_v_title")
            adm_trans = st.text_area("视频转录文字稿", key="adm_v_trans", height=100)
            if st.button("🚀 一键提取入库", use_container_width=True):
                if adm_url and adm_title:
                    res = ctx["pipeline"].process_new_video(
                        url=adm_url,
                        title=adm_title,
                        transcript_text=adm_trans if adm_trans else None
                    )
                    st.info(res.get("message", "处理完成"))
                else:
                    st.error("请填写链接与标题")

            if st.button("🔄 重建全文检索索引", use_container_width=True):
                cnt = ctx["pkg_mgr"].sync_to_database()
                st.success(f"索引重构完成: {cnt}")

# ------------------------------------------------------------------------------
# 6. Main Minimalist Chat Interface
# ------------------------------------------------------------------------------

# Top Minimalist Header & Expert Model Selector (Gemini / ChatGPT Style)
top_col1, top_col2 = st.columns([1.6, 1.2])

with top_col1:
    st.markdown(f"### {selected_expert['avatar']} **Horizon · {selected_expert['name']}**")
    st.caption(f"✨ 当前对话模型：`{ctx['config'].llm.model}` · 知识库：`{selected_expert['badge']}`")

with top_col2:
    # Model / Expert Selector Pill
    expert_options = list(EXPERTS_REGISTRY.keys())
    selected_idx = expert_options.index(st.session_state.selected_expert_id)
    new_expert_id = st.selectbox(
        "选择专家与知识库 (Expert Knowledge Base):",
        options=expert_options,
        index=selected_idx,
        format_func=lambda k: f"{EXPERTS_REGISTRY[k]['avatar']} {EXPERTS_REGISTRY[k]['name']}"
    )
    if new_expert_id != st.session_state.selected_expert_id:
        st.session_state.selected_expert_id = new_expert_id
        st.rerun()

st.markdown("---")

active_cid = st.session_state.current_conversation_id
messages = ctx["conv_mgr"].get_messages(active_cid) if active_cid else []

# Empty State: Hero Greeting & Quick Suggestion Cards (Like Gemini / ChatGPT)
if len(messages) == 0:
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-avatar">{selected_expert['avatar']}</div>
        <div class="hero-title">你好，我是 {selected_expert['name']}</div>
        <div class="hero-subtitle">{selected_expert['description']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### 💡 推荐提问 (点击直接发起深度研判):")
    cols = st.columns(2)
    sample_prompts = selected_expert["sample_prompts"]
    for i, p in enumerate(sample_prompts):
        col_target = cols[i % 2]
        with col_target:
            if st.button(f"📌 {p}", key=f"quick_prompt_{i}", use_container_width=True):
                # Trigger question directly
                st.session_state["pending_user_input"] = p
                st.rerun()

# Display Chat History
for msg in messages:
    if msg["role"] == "user":
        with st.chat_message("user"):
            st.markdown(msg["content"])
    else:
        with st.chat_message("assistant", avatar=selected_expert["avatar"]):
            st.markdown(msg["content"])
            if msg.get("citations"):
                with st.expander("📚 查阅支持该回答的视频证据链与时间戳出处"):
                    for c in msg["citations"]:
                        cat = c.get("category", "")
                        title = c.get("title", "")
                        date = f" · 📅 {c.get('publish_date')}" if c.get('publish_date') else ""
                        ts = f" · ⏱️ {c.get('timestamp')}" if c.get('timestamp') else ""
                        st.markdown(f"**[{cat}] {title}**{date}{ts}")
                        if c.get("video_id"):
                            url_part = f" · [点击查看原视频]({c.get('video_url')})" if c.get("video_url") else ""
                            st.caption(f"视频ID: `{c.get('video_id')}`{url_part} · 校验状态: `{c.get('verification_status')}`")
                        if c.get("verbatim_quote"):
                            st.markdown(f"> *\"{c.get('verbatim_quote')}\"*")
                        st.markdown("---")

# Handle Quick Prompt Clicks or Chat Input
user_query = None
if "pending_user_input" in st.session_state and st.session_state["pending_user_input"]:
    user_query = st.session_state["pending_user_input"]
    del st.session_state["pending_user_input"]
else:
    user_query = st.chat_input(f"向 {selected_expert['name']} 提问（例如：宏观逻辑、商业模式、估值锚点）...")

if user_query:
    # 1. Show user message
    with st.chat_message("user"):
        st.markdown(user_query)

    # Set title if first message
    if len(messages) == 0:
        short_title = user_query[:16] + ("..." if len(user_query) > 16 else "")
        ctx["conv_mgr"].update_title(active_cid, short_title)

    ctx["conv_mgr"].add_message(active_cid, "user", user_query)

    # 2. Generate response with selected expert persona & knowledge base
    with st.chat_message("assistant", avatar=selected_expert["avatar"]):
        with st.spinner(f"{selected_expert['name']} 正在检索知识库因果框架并推演分析..."):
            # Load specific system prompt for this expert
            prompt_path = Path("prompts") / selected_expert["prompt_file"]
            expert_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None

            resp = ctx["expert_engine"].answer_question(
                question=user_query,
                topic=selected_expert["topic_filter"],
                system_prompt=expert_prompt
            )

            citations_md = format_citations_markdown(resp.citations)
            full_answer = resp.answer_text + citations_md
            st.markdown(full_answer)

            ctx["conv_mgr"].add_message(
                conversation_id=active_cid,
                role="assistant",
                content=resp.answer_text,
                model_name=resp.model_name,
                citations=[c.model_dump() for c in resp.citations],
                tokens_used=resp.tokens_used
            )
    st.rerun()
