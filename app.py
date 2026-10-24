"""
app.py
Horizon: Ultra-Minimalist AI Investment Expert Platform (Gemini / ChatGPT Style)
- Protected behind secure login.
- Centered dialogue box & model selector on initial/empty page (just like Gemini).
- In conversation: User query on RIGHT (blue bubble), Expert answer on LEFT (neutral card), no names displayed.
- Left sidebar: New chat, logged-in account's history, bottom-left account manager (avatar, password change, logout).
- Deep suppression of Streamlit Community Cloud 'Manage app' popup and all UI chrome.
"""

import html
import os
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
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
# 1. Page Configuration & Deep UI Chrome Suppression
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Horizon",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Deep CSS to hide Streamlit Header, Footer, Toolbar, and Cloud Badges
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
    div[style*="position:fixed"][style*="bottom:"][style*="right:"],
    div[style*="position: fixed"][style*="right:"][style*="bottom:"],
    div[style*="position:fixed"][style*="right:"][style*="bottom:"] {
        display: none !important;
        visibility: hidden !important;
        opacity: 0 !important;
        pointer-events: none !important;
    }

    div[data-testid="stBottom"] {
        display: block !important;
        visibility: visible !important;
        opacity: 1 !important;
        pointer-events: auto !important;
    }

    /* Textarea & prompt card styling */
    .stTextArea textarea {
        border-radius: 14px !important;
        border: 1px solid #CBD5E1 !important;
        font-size: 15px !important;
        line-height: 1.5 !important;
        padding: 12px 14px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.03) !important;
        resize: none !important;
    }
    .stTextArea textarea:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 2px rgba(37,99,235,0.18) !important;
    }

    /* Clean container layout */
    .block-container {
        padding-top: 1rem;
        padding-bottom: 5rem;
        max-width: 860px;
    }

    /* Minimalist User Bubble (Right Aligned, Blue, No Name) */
    .user-bubble-box {
        display: flex;
        justify-content: flex-end;
        width: 100%;
        margin: 12px 0;
    }
    .user-bubble {
        background-color: #2563EB;
        color: #FFFFFF !important;
        padding: 10px 16px;
        border-radius: 18px 18px 4px 18px;
        max-width: 78%;
        word-break: break-word;
        font-size: 15px;
        line-height: 1.55;
        box-shadow: 0 1px 2px rgba(0,0,0,0.06);
    }

    /* Minimalist Assistant Bubble (Left Aligned, Neutral Card, No Name) */
    .assistant-bubble-box {
        display: flex;
        justify-content: flex-start;
        width: 100%;
        margin: 12px 0;
    }
    .assistant-bubble {
        background-color: #F8FAFC;
        border: 1px solid #E2E8F0;
        color: #0F172A !important;
        padding: 14px 18px;
        border-radius: 18px 18px 18px 4px;
        max-width: 88%;
        word-break: break-word;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }
</style>
""", unsafe_allow_html=True)

# Continuous JavaScript to eliminate the floating 'Manage app' button on Streamlit Cloud
components.html("""
<script>
function suppressManageApp() {
    try {
        const selList = [
            '[data-testid="manage-app-button"]',
            'iframe[title="manage-app"]',
            'button[title*="Manage app"]',
            'button[title*="manage"]',
            'div[class*="viewerBadge"]',
            'div[class*="manage-app"]',
            '.viewerBadge_container__1QSob',
            '.styles_viewerBadge__1yB5_'
        ];
        
        selList.forEach(s => {
            document.querySelectorAll(s).forEach(el => { el.style.display = 'none'; el.remove(); });
        });
        
        if (window.parent && window.parent.document) {
            const pDoc = window.parent.document;
            selList.forEach(s => {
                pDoc.querySelectorAll(s).forEach(el => { el.style.display = 'none'; el.remove(); });
            });
            pDoc.querySelectorAll('button, a, div, iframe').forEach(el => {
                const text = el.innerText || el.getAttribute('title') || '';
                if (text.includes('Manage app') || text.includes('Streamlit Community Cloud')) {
                    el.style.display = 'none';
                    el.remove();
                }
            });
        }
    } catch (e) {}
}
suppressManageApp();
setInterval(suppressManageApp, 600);
</script>
""", height=0, width=0)

# ------------------------------------------------------------------------------
# 2. Knowledge Base & Expert Registry
# ------------------------------------------------------------------------------
EXPERTS_REGISTRY = {
    "horizon_macro": {
        "id": "horizon_macro",
        "name": "Horizon 宏观策略",
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
    try:
        conv_mgr.clean_empty_conversations()
    except Exception:
        pass
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
# 5. Minimalist Centered Login Screen
# ------------------------------------------------------------------------------
if not st.session_state.authenticated:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1, 1.2, 1])
    with c2:
        st.markdown("""
        <div style="text-align: center; margin-bottom: 1.8rem;">
            <div style="font-size: 2.5rem; margin-bottom: 0.2rem;">🧭</div>
            <h2 style="margin: 0; font-size: 1.5rem; color: #0F172A; font-weight: 700;">Horizon</h2>
            <p style="color: #64748B; font-size: 0.9rem; margin-top: 0.3rem;">私密 AI 投资决策专家</p>
        </div>
        """, unsafe_allow_html=True)

        with st.form("login_form", clear_on_submit=False):
            u_input = st.text_input("账号", placeholder="请输入账号", value="admin")
            p_input = st.text_input("密码", type="password", placeholder="请输入密码")
            submit = st.form_submit_button("登 录", use_container_width=True, type="primary")

            if submit:
                user = ctx["auth_mgr"].authenticate(u_input, p_input)
                if user:
                    st.session_state.authenticated = True
                    st.session_state.username = user["username"]
                    st.rerun()
                else:
                    st.error("账号或密码不正确。")
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
    # 1. New Chat Pill
    if st.button("➕ 新建对话", use_container_width=True, type="primary"):
        st.session_state.current_conversation_id = None
        st.rerun()

    st.markdown("---")
    st.caption("🕒 **历史记录**")

    # 2. Logged-in User's Conversation History List
    user_convs = ctx["conv_mgr"].list_conversations(user_id=current_user)
    history_convs = [c for c in user_convs if c.get("msg_count", 0) > 0]
    
    if not history_convs:
        st.caption("暂无历史记录，提问后自动保存")
    else:
        for c in history_convs:
            cid = c["conversation_id"]
            title = c["title"] if c.get("title") else "投资研判"
            title = title[:14] + ("..." if len(title) > 14 else "")
            is_active = (cid == st.session_state.current_conversation_id)
            btn_label = f"💬 **{title}**" if is_active else f"💬 {title}"
            if st.button(btn_label, key=f"hist_{cid}", use_container_width=True):
                st.session_state.current_conversation_id = cid
                st.rerun()

    if st.session_state.current_conversation_id:
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🗑️ 删除此记录", use_container_width=True):
            ctx["conv_mgr"].delete_conversation(st.session_state.current_conversation_id)
            st.session_state.current_conversation_id = None
            st.rerun()

    # 3. Bottom-Left Personal Account Management
    st.markdown("<br><br><br><br>", unsafe_allow_html=True)
    st.markdown("---")
    with st.expander(f"{st.session_state.user_avatar} **{current_user}**", expanded=False):
        st.caption(f"当前登录账号：`{current_user}`")

        # Avatar Choice
        avatar_opts = ["👤", "💼", "📈", "🧭", "🦁", "🦉", "🚀"]
        cur_idx = avatar_opts.index(st.session_state.user_avatar) if st.session_state.user_avatar in avatar_opts else 0
        new_av = st.selectbox("修改头像图标", options=avatar_opts, index=cur_idx)
        if new_av != st.session_state.user_avatar:
            st.session_state.user_avatar = new_av
            st.rerun()

        # Change Password
        new_pwd = st.text_input("设置新密码", type="password", key="chg_pwd")
        if st.button("更新密码", key="btn_chg_pwd", use_container_width=True):
            if new_pwd and len(new_pwd) >= 6:
                ctx["auth_mgr"].change_password(current_user, new_pwd)
                st.success("密码更新成功！")
            else:
                st.warning("密码至少为 6 位。")

        # Logout
        st.markdown("<br>", unsafe_allow_html=True)
        if st.button("🚪 退出登录", key="btn_logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.username = None
            st.session_state.current_conversation_id = None
            st.rerun()

# ==========================================
# MAIN CHAT AREA (Ultra-Minimalist)
# ==========================================

active_cid = st.session_state.current_conversation_id
messages = ctx["conv_mgr"].get_messages(active_cid) if active_cid else []

# Function to execute user query
def run_query(query_text: str):
    if not query_text or not query_text.strip():
        return

    # If this is a new conversation session, create it in DB now!
    cid = st.session_state.current_conversation_id
    if not cid:
        short_title = query_text.strip()[:16] + ("..." if len(query_text.strip()) > 16 else "")
        cid = ctx["conv_mgr"].create_conversation(title=short_title, user_id=current_user)
        st.session_state.current_conversation_id = cid

    # Save user message
    ctx["conv_mgr"].add_message(cid, "user", query_text.strip())

    # Generate Expert Response
    prompt_path = Path("prompts") / selected_expert["prompt_file"]
    expert_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None

    with st.spinner(f"{selected_expert['name']} 正在研判分析..."):
        resp = ctx["expert_engine"].answer_question(
            question=query_text.strip(),
            topic=selected_expert["topic_filter"],
            system_prompt=expert_prompt
        )

    ctx["conv_mgr"].add_message(
        conversation_id=cid,
        role="assistant",
        content=resp.answer_text,
        model_name=resp.model_name,
        citations=[c.model_dump() for c in resp.citations],
        tokens_used=resp.tokens_used
    )
    st.rerun()

# ------------------------------------------------------------------------------
# CASE A: Starting Page (Empty Conversation - Dialog Box In Center, Like Gemini)
# ------------------------------------------------------------------------------
if len(messages) == 0:
    st.markdown("<div style='height: 12vh;'></div>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center; margin-bottom: 1.5rem;">
        <h2 style="font-size: 1.8rem; font-weight: 700; color: #0F172A; margin-bottom: 0.4rem;">有什么投资问题想与专家探讨？</h2>
        <p style="color: #64748B; font-size: 0.95rem;">基于多位博主全量视频蒸馏的因果模型与估值决策</p>
    </div>
    """, unsafe_allow_html=True)

    # Centered Model Selector & Input Box (Just like Gemini)
    col_l, col_center, col_r = st.columns([1, 2.6, 1])
    with col_center:
        # Knowledge Base Selector Pill
        expert_options = list(EXPERTS_REGISTRY.keys())
        cur_exp_idx = expert_options.index(st.session_state.selected_expert_id)
        new_exp_id = st.selectbox(
            "选择专家模型：",
            options=expert_options,
            index=cur_exp_idx,
            format_func=lambda k: f"{EXPERTS_REGISTRY[k]['avatar']} {EXPERTS_REGISTRY[k]['name']}",
            label_visibility="collapsed"
        )
        if new_exp_id != st.session_state.selected_expert_id:
            st.session_state.selected_expert_id = new_exp_id
            st.rerun()

        # Center Input Form
        with st.form("center_chat_form", clear_on_submit=True):
            user_input_center = st.text_area(
                "输入问题...",
                placeholder=f"向 {selected_expert['name']} 提问（例如：宏观逻辑、商业模式、估值安全边际）...",
                height=95,
                label_visibility="collapsed"
            )
            c_send = st.form_submit_button("发 送 提 问", use_container_width=True, type="primary")
            if c_send and user_input_center.strip():
                run_query(user_input_center.strip())

        # 4 Quick clickable suggestion cards
        st.markdown("<br><p style='color: #64748B; font-size: 0.88rem; margin-bottom: 0.6rem;'>💡 推荐研判：</p>", unsafe_allow_html=True)
        sp_cols = st.columns(2)
        for i, p in enumerate(selected_expert["sample_prompts"]):
            with sp_cols[i % 2]:
                if st.button(f"📌 {p}", key=f"sp_btn_{i}", use_container_width=True):
                    run_query(p)

# ------------------------------------------------------------------------------
# CASE B: In-Conversation Flow (Messages Rendered, Input at Bottom)
# ------------------------------------------------------------------------------
else:
    # Render Chat History
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        citations = msg.get("citations", [])

        if role == "user":
            # 1. User question: Right-aligned blue bubble, no name
            esc_text = html.escape(content).replace("\n", "<br>")
            st.markdown(f"""
            <div class="user-bubble-box">
                <div class="user-bubble">{esc_text}</div>
            </div>
            """, unsafe_allow_html=True)
        else:
            # 2. Expert answer: Left-aligned neutral card, no name
            col_asst, col_empty = st.columns([4.2, 0.8])
            with col_asst:
                st.markdown(f"""
                <div class="assistant-bubble-box">
                    <div class="assistant-bubble">
                """, unsafe_allow_html=True)
                
                # Render full markdown inside the assistant card
                citations_md = format_citations_markdown(citations)
                st.markdown(content + citations_md)
                
                st.markdown("""
                    </div>
                </div>
                """, unsafe_allow_html=True)

    st.markdown("<br><br>", unsafe_allow_html=True)

    # Model selector pill right above the bottom input box (like Gemini)
    b_col1, b_col2 = st.columns([1.5, 1])
    with b_col2:
        expert_options = list(EXPERTS_REGISTRY.keys())
        cur_exp_idx = expert_options.index(st.session_state.selected_expert_id)
        new_exp_id_bottom = st.selectbox(
            "切换当前专家：",
            options=expert_options,
            index=cur_exp_idx,
            format_func=lambda k: f"{EXPERTS_REGISTRY[k]['avatar']} {EXPERTS_REGISTRY[k]['name']}",
            label_visibility="collapsed",
            key="bottom_exp_select"
        )
        if new_exp_id_bottom != st.session_state.selected_expert_id:
            st.session_state.selected_expert_id = new_exp_id_bottom
            st.rerun()

    # Pinned Bottom Chat Input
    bottom_input = st.chat_input(f"向 {selected_expert['name']} 继续提问...")
    if bottom_input and bottom_input.strip():
        run_query(bottom_input.strip())
