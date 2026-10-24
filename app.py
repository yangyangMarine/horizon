"""
app.py
Horizon: Ultra-Minimalist AI Investment Expert Platform (ChatGPT / Gemini Style)
- Protected behind secure login.
- Left sidebar: New chat, logged-in user's conversation history, bottom-left account manager (avatar, password change, logout).
- Chat area: User query right-aligned (colored), Expert answer left-aligned (neutral), no names displayed.
- Model selector: Seamlessly switch knowledge bases (Horizon Macro, Aili Investor, Liquidity).
- Strict suppression of Streamlit chrome, GitHub links, and the bottom-right 'Manage app' popup.
"""

import os
from pathlib import Path
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from src.macro_expert.auth import AuthManager
from src.macro_expert.citations import format_citations_markdown
from src.macro_expert.config import load_config
from src.macro_expert.conversations import ConversationManager
from src.macro_expert.cost_control import CostController
from src.macro_expert.database import Database
from src.macro_expert.expert import MacroExpertEngine
from src.macro_expert.knowledge_package import KnowledgePackageManager
from src.macro_expert.llm import get_llm_adapter
from src.macro_expert.retrieval import HybridRetriever

# ------------------------------------------------------------------------------
# 1. Page Configuration & Absolute UI Chrome Suppression
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Horizon - AI 投资决策专家",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aggressive CSS to hide all default Streamlit chrome, GitHub fork links, and Manage app popups
st.markdown("""
<style>
    /* Complete suppression of Streamlit Header, Footer, Menu, and Cloud Badges */
    #MainMenu { display: none !important; visibility: hidden !important; }
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    .stDeployButton { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    
    /* Suppress Streamlit Community Cloud 'Manage app' button and bottom-right badges */
    iframe[title="manage-app"] { display: none !important; visibility: hidden !important; }
    [data-testid="manage-app-button"] { display: none !important; visibility: hidden !important; }
    div[class*="viewerBadge"] { display: none !important; visibility: hidden !important; }
    div[class*="manage-app"] { display: none !important; visibility: hidden !important; }
    .viewerBadge_container__1QSob { display: none !important; visibility: hidden !important; }
    .styles_viewerBadge__1yB5_ { display: none !important; visibility: hidden !important; }
    button[title*="Streamlit Community Cloud"] { display: none !important; visibility: hidden !important; }
    div[style*="position: fixed"][style*="bottom:"][style*="right:"],
    div[style*="position:fixed"][style*="bottom:"][style*="right:"] {
        display: none !important;
        visibility: hidden !important;
    }

    /* Container sizing & responsive layout */
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 5rem;
        max-width: 860px;
    }

    /* Minimalist Chat Bubble Alignment */
    /* 1. User Message: Float Right, distinct blue color, no avatar/name */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]),
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from user"]) {
        flex-direction: row-reverse !important;
        text-align: left !important;
        margin-left: auto !important;
        margin-right: 0 !important;
        max-width: 78% !important;
        background-color: #2563EB !important;
        border: none !important;
        border-radius: 18px 18px 4px 18px !important;
        padding: 0.75rem 1.15rem !important;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06) !important;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) div {
        color: #FFFFFF !important;
        font-size: 0.96rem !important;
        line-height: 1.5 !important;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-user"]) div[data-testid="stChatMessageAvatar"] {
        display: none !important;
    }

    /* 2. Assistant Message: Float Left, clean neutral gray card, no avatar/name */
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]),
    div[data-testid="stChatMessage"]:has([aria-label="Chat message from assistant"]) {
        flex-direction: row !important;
        text-align: left !important;
        margin-right: auto !important;
        margin-left: 0 !important;
        max-width: 90% !important;
        background-color: #F8FAFC !important;
        border: 1px solid #E2E8F0 !important;
        border-radius: 18px 18px 18px 4px !important;
        padding: 1rem 1.25rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02) !important;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) p,
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) div {
        color: #1E293B !important;
        font-size: 0.96rem !important;
        line-height: 1.6 !important;
    }
    div[data-testid="stChatMessage"]:has(div[data-testid="chatAvatarIcon-assistant"]) div[data-testid="stChatMessageAvatar"] {
        display: none !important;
    }

    /* Hero greeting card */
    .hero-card {
        text-align: center;
        padding: 2.5rem 1rem 1.5rem 1rem;
        margin: 1.5rem auto;
    }
    .hero-avatar {
        font-size: 3rem;
        margin-bottom: 0.5rem;
    }
    .hero-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #0F172A;
        margin-bottom: 0.4rem;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #64748B;
        max-width: 580px;
        margin: 0 auto 1.8rem auto;
        line-height: 1.5;
    }
</style>
""", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# 2. Knowledge Base & Expert Registry
# ------------------------------------------------------------------------------
EXPERTS_REGISTRY = {
    "horizon_macro": {
        "id": "horizon_macro",
        "name": "Horizon 宏观策略",
        "avatar": "🧭",
        "badge": "宏观流动性 · 美债收益率 · 周期演进",
        "description": "基于宏观研判视频蒸馏，专注于美联储净流动性、主权债务利息螺旋与长端收益率因果推演。",
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
        "name": "Aili (艾莉) 投资决策",
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
        "name": "全球流动性智囊",
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
# 3. Singleton Context Loader
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

    return {
        "config": config,
        "db": db,
        "auth_mgr": auth_mgr,
        "conv_mgr": conv_mgr,
        "expert_engine": expert_engine
    }

ctx = get_app_context()

# ------------------------------------------------------------------------------
# 4. Session State Management
# ------------------------------------------------------------------------------
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = None
if "user_avatar" not in st.session_state:
    st.session_state.user_avatar = "👤"
if "selected_expert_id" not in st.session_state:
    st.session_state.selected_expert_id = "horizon_macro"
if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None

# ------------------------------------------------------------------------------
# 5. Minimalist Centered Login Screen (Preserved as requested)
# ------------------------------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown("<br><br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <div style="font-size: 2.8rem; margin-bottom: 0.3rem;">🧭</div>
            <h2 style="margin: 0; font-size: 1.6rem; color: #0F172A; font-weight: 700;">Horizon 投资专家</h2>
            <p style="color: #64748B; font-size: 0.92rem; margin-top: 0.4rem;">私密便携式投研决策中枢</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            u_input = st.text_input("账号 (Username)", placeholder="请输入账号", value="admin")
            p_input = st.text_input("密码 (Password)", type="password", placeholder="请输入密码")
            submit = st.form_submit_button("登录验证", use_container_width=True, type="primary")

            if submit:
                user = ctx["auth_mgr"].authenticate(u_input, p_input)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.rerun()
                else:
                    st.error("账号或密码不正确，请重新输入。")
    st.stop()

# ------------------------------------------------------------------------------
# 6. Authenticated Minimalist UI Layout
# ------------------------------------------------------------------------------
current_user = st.session_state.username or "admin"
selected_expert = EXPERTS_REGISTRY.get(st.session_state.selected_expert_id, EXPERTS_REGISTRY["horizon_macro"])

# ==========================================
# LEFT SIDEBAR: History & Account (Bottom-Left)
# ==========================================
with st.sidebar:
    # 1. New Chat Button
    if st.button("➕ 新建对话", use_container_width=True, type="primary"):
        new_cid = ctx["conv_mgr"].create_conversation(title="新研判对话", user_id=current_user)
        st.session_state.current_conversation_id = new_cid
        st.rerun()

    st.markdown("---")
    st.caption("📜 **历史研判记录**")

    # 2. Logged-in User's Conversation History Only
    user_convs = ctx["conv_mgr"].list_conversations(user_id=current_user)
    if not user_convs:
        init_cid = ctx["conv_mgr"].create_conversation(title="初始宏观研判", user_id=current_user)
        st.session_state.current_conversation_id = init_cid
        user_convs = ctx["conv_mgr"].list_conversations(user_id=current_user)

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

    # Clear current chat
    if st.session_state.current_conversation_id:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ 删除当前记录", use_container_width=True):
            ctx["conv_mgr"].delete_conversation(st.session_state.current_conversation_id)
            st.session_state.current_conversation_id = None
            st.rerun()

    # 3. Bottom-Left Personal Account Management
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown("---")
    with st.expander(f"{st.session_state.user_avatar} **{current_user} (个人账号)**", expanded=False):
        st.caption(f"当前登录账号：`{current_user}`")

        # Avatar selector
        avatar_choice = st.selectbox(
            "个人头像图标",
            options=["👤", "💼", "📈", "🧭", "🦁", "🦉", "🚀"],
            index=["👤", "💼", "📈", "🧭", "🦁", "🦉", "🚀"].index(st.session_state.user_avatar) if st.session_state.user_avatar in ["👤", "💼", "📈", "🧭", "🦁", "🦉", "🚀"] else 0
        )
        if avatar_choice != st.session_state.user_avatar:
            st.session_state.user_avatar = avatar_choice
            st.rerun()

        # Change Password
        new_pwd = st.text_input("新登录密码", type="password", key="new_pwd_inp")
        if st.button("更新密码", key="update_pwd_btn", use_container_width=True):
            if new_pwd and len(new_pwd) >= 6:
                ctx["auth_mgr"].change_password(current_user, new_pwd)
                st.success("密码更新成功！")
            else:
                st.warning("密码长度至少为 6 位。")

        # Logout
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 退出登录", key="logout_btn", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.current_conversation_id = None
            st.rerun()

# ==========================================
# MAIN CHAT AREA (Ultra-Minimalist)
# ==========================================

# Top Header: Sleek Expert Knowledge Selector
top_col1, top_col2 = st.columns([1.5, 1.2])
with top_col1:
    st.markdown(f"#### {selected_expert['avatar']} **{selected_expert['name']}**")
    st.caption(f"🧠 当前知识库：`{selected_expert['badge']}`")

with top_col2:
    expert_options = list(EXPERTS_REGISTRY.keys())
    selected_idx = expert_options.index(st.session_state.selected_expert_id)
    new_expert_id = st.selectbox(
        "切换专家模型与知识库:",
        options=expert_options,
        index=selected_idx,
        format_func=lambda k: f"{EXPERTS_REGISTRY[k]['avatar']} {EXPERTS_REGISTRY[k]['name']}",
        label_visibility="collapsed"
    )
    if new_expert_id != st.session_state.selected_expert_id:
        st.session_state.selected_expert_id = new_expert_id
        st.rerun()

st.markdown("---")

# Load Messages
active_cid = st.session_state.current_conversation_id
messages = ctx["conv_mgr"].get_messages(active_cid) if active_cid else []

# Empty State: Welcome Hero & Clickable Suggestions
if len(messages) == 0:
    st.markdown(f"""
    <div class="hero-card">
        <div class="hero-avatar">{selected_expert['avatar']}</div>
        <div class="hero-title">你好，我是 {selected_expert['name']}</div>
        <div class="hero-subtitle">{selected_expert['description']}</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("##### 💡 推荐提问 (点击即可直接发送):")
    cols = st.columns(2)
    sample_prompts = selected_expert["sample_prompts"]
    for i, p in enumerate(sample_prompts):
        col_target = cols[i % 2]
        with col_target:
            if st.button(f"📌 {p}", key=f"quick_prompt_{i}", use_container_width=True):
                st.session_state["pending_user_input"] = p
                st.rerun()

# Render Chat History (User Right / Blue, Expert Left / Gray, NO NAMES DISPLAYED)
for msg in messages:
    role = msg["role"]
    content = msg["content"]
    citations = msg.get("citations", [])

    if role == "user":
        # User message: Right aligned bubble with color
        with st.chat_message("user"):
            st.markdown(content)
    else:
        # Expert answer: Left aligned neutral card, no name
        with st.chat_message("assistant"):
            st.markdown(content)
            if citations:
                with st.expander("📚 查看视频引证与时间戳出处"):
                    for c in citations:
                        cat = c.get("category", "")
                        title = c.get("title", "")
                        date = f" · 📅 {c.get('publish_date')}" if c.get('publish_date') else ""
                        ts = f" · ⏱️ {c.get('timestamp')}" if c.get('timestamp') else ""
                        st.markdown(f"**[{cat}] {title}**{date}{ts}")
                        if c.get("video_id"):
                            url_part = f" · [点击观看原视频]({c.get('video_url')})" if c.get("video_url") else ""
                            st.caption(f"视频编号: `{c.get('video_id')}`{url_part} · 校验状态: `{c.get('verification_status')}`")
                        if c.get("verbatim_quote"):
                            st.markdown(f"> *\"{c.get('verbatim_quote')}\"*")
                        st.markdown("---")

# Handle Input
user_query = None
if "pending_user_input" in st.session_state and st.session_state["pending_user_input"]:
    user_query = st.session_state["pending_user_input"]
    del st.session_state["pending_user_input"]
else:
    user_query = st.chat_input(f"向 {selected_expert['name']} 提问...")

if user_query:
    # 1. Render User Message immediately
    with st.chat_message("user"):
        st.markdown(user_query)

    # Update conversation title if first message
    if len(messages) == 0 and active_cid:
        short_title = user_query[:16] + ("..." if len(user_query) > 16 else "")
        ctx["conv_mgr"].update_title(active_cid, short_title)

    ctx["conv_mgr"].add_message(active_cid, "user", user_query)

    # 2. Generate and render Expert Response
    with st.chat_message("assistant"):
        with st.spinner(f"{selected_expert['name']} 正在研判分析..."):
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
