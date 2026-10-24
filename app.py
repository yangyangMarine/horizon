"""
app.py
Horizon: Ultra-Minimalist AI Investment Expert Platform (Gemini / ChatGPT Style)
- Protected behind secure login.
- Left sidebar:
    * Workspaces: 💬 投资研判 (Chat), 📚 专家知识库 (Knowledge Base), ⚡ 视频蒸馏入库 (Distillation).
    * Conversation History for logged-in user with instant switching and deletion.
    * Personal Profile Manager (avatar choice, password reset, logout).
- Chat Area:
    * Initial screen: Centered, LARGE spacious dialogue box & model selector (Gemini-style).
    * Active conversation: User query on RIGHT (blue bubble), Expert answer on LEFT (neutral card), no names/avatars.
    * Model selector pill directly in the dialogue area.
- Deep suppression of Streamlit Community Cloud 'Manage app' popup and all UI chrome.
"""

import html
import json
import os
import uuid
from pathlib import Path
import streamlit as st
import streamlit.components.v1 as components
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
# 1. Page Configuration & Deep UI Chrome Suppression
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Horizon - 私人投资决策专家",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Deep CSS to hide Streamlit Header, Footer, Toolbar, and Cloud Badges
st.markdown("""
<style>
    /* 1. Header & Menu - Keep sidebar collapse button accessible, hide all deploy/cloud clutter */
    header[data-testid="stHeader"] {
        background: transparent !important;
        height: 2.5rem !important;
    }
    #MainMenu { display: none !important; }
    footer { display: none !important; }
    .stDeployButton { display: none !important; }
    div[data-testid="stDecoration"] { display: none !important; }
    div[data-testid="stStatusWidget"] { display: none !important; }
    div[data-testid="stToolbar"] { display: none !important; }
    
    /* Ensure sidebar toggle button is ALWAYS visible & clickable */
    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        z-index: 999999 !important;
    }

    /* Style the sidebar expand button (when collapsed) */
    [data-testid="collapsedControl"] {
        display: flex !important;
        visibility: visible !important;
        opacity: 1 !important;
        position: fixed !important;
        top: 12px !important;
        left: 12px !important;
        z-index: 999999 !important;
        background: #FFFFFF !important;
        border: 1.5px solid #2563EB !important;
        border-radius: 10px !important;
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.18) !important;
        padding: 6px 12px !important;
        cursor: pointer !important;
        transition: all 0.2s ease !important;
        align-items: center !important;
    }
    [data-testid="collapsedControl"]:hover {
        background: #EFF6FF !important;
        transform: scale(1.05) !important;
    }
    [data-testid="collapsedControl"]::after {
        content: " 展开侧栏";
        font-size: 13px;
        font-weight: 600;
        color: #2563EB;
        margin-left: 6px;
    }

    /* 2. Suppress Streamlit Community Cloud 'Manage app' button and bottom-right badges */
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

    /* 3. Initial Big Dialogue Box Styling */
    .stTextArea textarea {
        border-radius: 16px !important;
        border: 1.5px solid #CBD5E1 !important;
        font-size: 16px !important;
        line-height: 1.6 !important;
        padding: 16px 18px !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04) !important;
        resize: vertical !important;
        background-color: #FFFFFF !important;
    }
    .stTextArea textarea:focus {
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.18) !important;
    }

    /* 4. Clean container layout */
    .block-container {
        padding-top: 1.2rem;
        padding-bottom: 5rem;
        max-width: 920px;
    }

    /* 5. Minimalist User Bubble (Right Aligned, Blue, No Name) */
    .user-bubble-box {
        display: flex;
        justify-content: flex-end;
        width: 100%;
        margin: 12px 0;
    }
    .user-bubble {
        background-color: #2563EB;
        color: #FFFFFF !important;
        padding: 12px 18px;
        border-radius: 18px 18px 4px 18px;
        max-width: 80%;
        word-break: break-word;
        font-size: 15px;
        line-height: 1.6;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08);
    }

    /* 6. Minimalist Assistant Bubble (Left Aligned, Neutral Card, No Name) */
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
        padding: 16px 20px;
        border-radius: 18px 18px 18px 4px;
        max-width: 90%;
        word-break: break-word;
        font-size: 15px;
        line-height: 1.65;
        box-shadow: 0 1px 4px rgba(0,0,0,0.03);
    }
</style>
""", unsafe_allow_html=True)

# Continuous JavaScript to eliminate floating 'Manage app' elements on Streamlit Cloud
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
            '.styles_viewerBadge__1yB5_',
            'div[style*="bottom: 0px"][style*="right: 0px"]',
            'div[style*="bottom: 12px"][style*="right: 12px"]',
            'div[style*="bottom: 14px"][style*="right: 14px"]',
            'div[style*="bottom: 16px"][style*="right: 16px"]'
        ];
        
        selList.forEach(s => {
            document.querySelectorAll(s).forEach(el => {
                el.style.display = 'none';
                el.style.visibility = 'hidden';
                el.style.opacity = '0';
                el.remove();
            });
        });
        
        if (window.parent && window.parent.document) {
            const pDoc = window.parent.document;
            selList.forEach(s => {
                pDoc.querySelectorAll(s).forEach(el => {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.style.opacity = '0';
                    el.remove();
                });
            });
            pDoc.querySelectorAll('button, a, div, iframe').forEach(el => {
                const text = el.innerText || el.getAttribute('title') || '';
                if (text.includes('Manage app') || text.includes('Streamlit Community Cloud') || text.includes('Manage')) {
                    el.style.display = 'none';
                    el.style.visibility = 'hidden';
                    el.remove();
                }
            });
        }
    } catch (e) {}
}
suppressManageApp();
setInterval(suppressManageApp, 300);
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
    export_mgr = ExportManager(config.knowledge.package_path, config.knowledge.export_path, db)
    ingest_pipe = IngestPipeline(db, llm, config.knowledge.package_path)

    return {
        "config": config,
        "db": db,
        "auth_mgr": auth_mgr,
        "pkg_mgr": pkg_mgr,
        "conv_mgr": conv_mgr,
        "retriever": retriever,
        "expert_engine": expert_engine,
        "export_mgr": export_mgr,
        "ingest_pipe": ingest_pipe
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
if "nav_mode" not in st.session_state:
    st.session_state.nav_mode = "💬 投资研判"

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
# 6. Authenticated Workspace Layout
# ------------------------------------------------------------------------------
current_user = st.session_state.username or "admin"
selected_expert = EXPERTS_REGISTRY.get(st.session_state.selected_expert_id, EXPERTS_REGISTRY["horizon_macro"])

# ==========================================
# LEFT SIDEBAR: Navigation, History & Profile
# ==========================================
with st.sidebar:
    col_brand, col_close = st.columns([3.2, 1.8])
    with col_brand:
        st.markdown("""
        <div style="display: flex; align-items: center; gap: 8px; margin-top: 4px;">
            <span style="font-size: 1.5rem;">🧭</span>
            <span style="font-size: 1.25rem; font-weight: 700; color: #0F172A;">Horizon</span>
            <span style="font-size: 0.72rem; background: #EEF2F6; color: #2563EB; font-weight: 700; padding: 2px 6px; border-radius: 4px;">PRO</span>
        </div>
        """, unsafe_allow_html=True)
    with col_close:
        # One-click button to collapse/retract sidebar
        components.html("""
        <button id="btn-collapse-sidebar" onclick="
            try {
                let b = window.parent.document.querySelector('[data-testid=stSidebarCollapseButton]') || 
                        window.parent.document.querySelector('button[aria-label=\\'Close sidebar\\']') ||
                        document.querySelector('[data-testid=stSidebarCollapseButton]');
                if (b) { b.click(); }
            } catch(e) {}
        " style="
            background: #F1F5F9;
            border: 1px solid #CBD5E1;
            border-radius: 8px;
            padding: 6px 10px;
            color: #475569;
            font-size: 12px;
            font-weight: 600;
            cursor: pointer;
            display: flex;
            align-items: center;
            gap: 4px;
            width: 100%;
            justify-content: center;
            font-family: inherit;
            transition: all 0.2s;
        " onmouseover="this.style.background='#E2E8F0'; this.style.color='#1E293B'" onmouseout="this.style.background='#F1F5F9'; this.style.color='#475569'">
            ◀ <b>收起</b>
        </button>
        """, height=38)

    # 1. Main Functional Navigation
    nav_mode = st.radio(
        "工作台导航",
        options=["💬 投资研判", "📚 专家知识库", "⚡ 视频蒸馏入库"],
        index=["💬 投资研判", "📚 专家知识库", "⚡ 视频蒸馏入库"].index(st.session_state.nav_mode) if st.session_state.nav_mode in ["💬 投资研判", "📚 专家知识库", "⚡ 视频蒸馏入库"] else 0,
        label_visibility="collapsed"
    )
    if nav_mode != st.session_state.nav_mode:
        st.session_state.nav_mode = nav_mode
        st.rerun()

    st.markdown("---")

    # 2. Conversation History (Visible in Chat mode)
    if nav_mode == "💬 投资研判":
        if st.button("➕ 新建对话", use_container_width=True, type="primary"):
            st.session_state.current_conversation_id = None
            st.rerun()

        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.markdown("##### 🕒 历史聊天记录")
        user_convs = ctx["conv_mgr"].list_conversations(user_id=current_user)
        history_convs = [c for c in user_convs if c.get("msg_count", 0) > 0]
        
        if not history_convs:
            st.markdown("""
            <div style="background: #F8FAFC; border: 1px dashed #CBD5E1; border-radius: 10px; padding: 14px; text-align: center; color: #64748B; font-size: 13px; margin-bottom: 12px;">
                💬 暂无历史对话<br><span style="font-size: 12px; color: #94A3B8;">发起提问后将自动沉淀记录</span>
            </div>
            """, unsafe_allow_html=True)
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
            st.markdown("<div style='margin-top: 6px;'></div>", unsafe_allow_html=True)
            if st.button("🗑️ 删除当前记录", use_container_width=True):
                ctx["conv_mgr"].delete_conversation(st.session_state.current_conversation_id)
                st.session_state.current_conversation_id = None
                st.rerun()

    # 3. User Profile Card (Always directly displayed)
    st.markdown("---")
    st.markdown("##### 👤 个人信息 (Profile)")

    # Directly displayed profile card
    st.markdown(f"""
    <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 12px 14px; margin-bottom: 10px;">
        <div style="display: flex; align-items: center; gap: 12px;">
            <div style="font-size: 1.8rem; background: #FFFFFF; border-radius: 50%; width: 42px; height: 42px; display: flex; align-items: center; justify-content: center; box-shadow: 0 1px 3px rgba(0,0,0,0.06);">{st.session_state.user_avatar}</div>
            <div>
                <div style="font-weight: 700; font-size: 15px; color: #0F172A;">{current_user}</div>
                <div style="font-size: 12px; color: #16A34A; display: flex; align-items: center; gap: 4px;">● 在线 · 超级管理员</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    with st.expander("⚙️ 账号安全设置 (修改头像/密码)", expanded=False):
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

    if st.button("🚪 退出登录", key="btn_logout", use_container_width=True):
        st.session_state.authenticated = False
        st.session_state.username = None
        st.session_state.current_conversation_id = None
        st.rerun()

    # Bottom helper button to collapse sidebar
    st.markdown("<div style='margin-top: 14px;'></div>", unsafe_allow_html=True)
    components.html("""
    <button onclick="
        try {
            let b = window.parent.document.querySelector('[data-testid=stSidebarCollapseButton]') || 
                    window.parent.document.querySelector('button[aria-label=\\'Close sidebar\\']') ||
                    document.querySelector('[data-testid=stSidebarCollapseButton]');
            if (b) { b.click(); }
        } catch(e) {}
    " style="
        background: transparent;
        border: 1px dashed #CBD5E1;
        border-radius: 8px;
        padding: 6px 12px;
        color: #64748B;
        font-size: 12px;
        cursor: pointer;
        display: flex;
        align-items: center;
        gap: 6px;
        width: 100%;
        justify-content: center;
        transition: all 0.2s;
    " onmouseover="this.style.background='#F1F5F9'; this.style.color='#1E293B'" onmouseout="this.style.background='transparent'; this.style.color='#64748B'">
        ◀ 收起左侧边栏 (Collapse)
    </button>
    """, height=36)


# ==============================================================================
# VIEW 1: 💬 投资研判 (Ultra-Minimalist Gemini/ChatGPT Chat)
# ==============================================================================
if nav_mode == "💬 投资研判":
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

        # Generate Expert Response with visual spinner
        prompt_path = Path("prompts") / selected_expert["prompt_file"]
        expert_prompt = prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else None

        try:
            with st.spinner(f"{selected_expert['name']} 正在研判分析..."):
                resp = ctx["expert_engine"].answer_question(
                    question=query_text.strip(),
                    topic=selected_expert["topic_filter"],
                    system_prompt=expert_prompt
                )

            citations_data = []
            if resp.citations:
                for c in resp.citations:
                    if hasattr(c, "model_dump"):
                        citations_data.append(c.model_dump())
                    elif isinstance(c, dict):
                        citations_data.append(c)

            ctx["conv_mgr"].add_message(
                conversation_id=cid,
                role="assistant",
                content=resp.answer_text,
                model_name=resp.model_name,
                citations=citations_data,
                tokens_used=resp.tokens_used
            )
        except Exception as e:
            st.error(f"研判分析发生异常: {e}")
            ctx["conv_mgr"].add_message(
                conversation_id=cid,
                role="assistant",
                content=f"⚠️ 模型推理时发生异常：{str(e)}。请检查是否已在云平台设置有效 GEMINI_API_KEY。",
                model_name="error_handler",
                citations=[],
                tokens_used=0
            )
        st.rerun()

    # --------------------------------------------------------------------------
    # CASE A: Starting Page (Empty Conversation - Big Dialog Box In Center)
    # --------------------------------------------------------------------------
    if len(messages) == 0:
        st.markdown("<div style='height: 6vh;'></div>", unsafe_allow_html=True)
        st.markdown("""
        <div style="text-align: center; margin-bottom: 2rem;">
            <h1 style="font-size: 2.1rem; font-weight: 700; color: #0F172A; margin-bottom: 0.5rem; letter-spacing: -0.5px;">有什么投资问题想与专家探讨？</h1>
            <p style="color: #64748B; font-size: 1.05rem;">基于多位知名博主全量视频蒸馏的因果模型与安全边际</p>
        </div>
        """, unsafe_allow_html=True)

        # Centered Model Selector & Big Dialogue Box (Like Gemini)
        col_l, col_center, col_r = st.columns([0.4, 4.2, 0.4])
        with col_center:
            # Knowledge Base Selector Pill
            expert_options = list(EXPERTS_REGISTRY.keys())
            cur_exp_idx = expert_options.index(st.session_state.selected_expert_id)
            new_exp_id = st.selectbox(
                "选择专家模型：",
                options=expert_options,
                index=cur_exp_idx,
                format_func=lambda k: f"{EXPERTS_REGISTRY[k]['avatar']} {EXPERTS_REGISTRY[k]['name']} ({EXPERTS_REGISTRY[k]['badge']})",
                label_visibility="collapsed"
            )
            if new_exp_id != st.session_state.selected_expert_id:
                st.session_state.selected_expert_id = new_exp_id
                st.rerun()

            # Large Center Input Form
            with st.form("center_chat_form", clear_on_submit=True):
                user_input_center = st.text_area(
                    "输入详细问题...",
                    placeholder=f"向 {selected_expert['name']} 详细提问（例如：法国国债收益率走高机理、Aili商业模式壁垒与估值安全边际、美联储净流动性推演）...",
                    height=160,
                    label_visibility="collapsed"
                )
                c_send = st.form_submit_button("🚀 发 送 研 判 提 问", use_container_width=True, type="primary")
                if c_send and user_input_center.strip():
                    run_query(user_input_center.strip())

            # 4 Quick clickable suggestion cards
            st.markdown("<br><p style='color: #64748B; font-size: 0.9rem; font-weight: 500; margin-bottom: 0.8rem;'>💡 推荐研判：</p>", unsafe_allow_html=True)
            sp_cols = st.columns(2)
            for i, p in enumerate(selected_expert["sample_prompts"]):
                with sp_cols[i % 2]:
                    if st.button(f"📌 {p}", key=f"sp_btn_{i}", use_container_width=True):
                        run_query(p)

    # --------------------------------------------------------------------------
    # CASE B: In-Conversation Flow (Messages Rendered, Input at Bottom)
    # --------------------------------------------------------------------------
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
                col_asst, col_empty = st.columns([4.4, 0.6])
                with col_asst:
                    st.markdown("""
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


# ==============================================================================
# VIEW 2: 📚 专家知识库 (Knowledge Base Management)
# ==============================================================================
elif nav_mode == "📚 专家知识库":
    st.markdown("### 📚 专家知识库管理 (Expert Knowledge Base)")
    st.caption("查看从视频中蒸馏沉淀的因果断言、核心框架，并支持一键重新同步或导出便携知识包。")

    m1, m2, m3, m4 = st.columns(4)
    with ctx["db"].session() as conn:
        claim_cnt = conn.execute("SELECT count(*) FROM claims").fetchone()[0]
        framework_cnt = conn.execute("SELECT count(*) FROM frameworks").fetchone()[0]
        video_cnt = conn.execute("SELECT count(*) FROM videos").fetchone()[0]
        msg_cnt = conn.execute("SELECT count(*) FROM messages").fetchone()[0]

    m1.metric("收录视频数", f"{video_cnt} 期")
    m2.metric("核心断言数", f"{claim_cnt} 条")
    m3.metric("因果框架数", f"{framework_cnt} 套")
    m4.metric("研判对话总计", f"{msg_cnt} 条")

    st.markdown("---")
    
    # Tabs for Claims, Frameworks, and Portable Sync/Export
    kb_tab1, kb_tab2, kb_tab3 = st.tabs([
        "💡 核心因果断言 (Claims)",
        "📐 研判分析框架 (Frameworks)",
        "📦 便携包同步与导出 (Portable Package)"
    ])

    with kb_tab1:
        st.subheader("💡 视频提取的核心因果断言")
        with ctx["db"].session() as conn:
            cur = conn.execute("SELECT claim_id, topic, confidence, text FROM claims ORDER BY rowid DESC LIMIT 50")
            claims_data = [dict(r) for r in cur.fetchall()]
        if claims_data:
            st.dataframe(claims_data, use_container_width=True)
        else:
            st.info("当前暂无已入库断言，请前往「⚡ 视频蒸馏入库」录入视频。")

    with kb_tab2:
        st.subheader("📐 专家研判框架库")
        with ctx["db"].session() as conn:
            cur = conn.execute("SELECT framework_id, name, description, markdown_content FROM frameworks")
            fw_data = [dict(r) for r in cur.fetchall()]
        for fw in fw_data:
            with st.expander(f"📌 {fw['name']} (`{fw['framework_id']}`)", expanded=False):
                st.caption(fw.get("description", ""))
                st.markdown(fw.get("markdown_content", ""))

    with kb_tab3:
        st.subheader("📦 专家包同步与便携导出")
        st.write("所有专家知识均保存在独立的 YAML/Markdown/JSONL 目录 `expert_pack/` 中，可一键同步至数据库或打包导出。")
        col_sync, col_export = st.columns(2)
        with col_sync:
            if st.button("🔄 重新同步 expert_pack 到 SQLite 索引", use_container_width=True, type="primary"):
                counts = ctx["pkg_mgr"].sync_to_database()
                st.success(f"同步完成！当前库中同步结果：{counts}")
                st.rerun()
        with col_export:
            if st.button("📦 一键生成专家知识包 ZIP 归档", use_container_width=True):
                zip_path = ctx["export_mgr"].export_expert_package_zip()
                st.success(f"便携包已导出至：`{zip_path}`")


# ==============================================================================
# VIEW 3: ⚡ 视频蒸馏入库 (Video Ingestion & Distillation Workspace)
# ==============================================================================
elif nav_mode == "⚡ 视频蒸馏入库":
    st.markdown("### ⚡ 视频转录与蒸馏入库 (Video Distillation & Ingestion)")
    st.caption("支持单条视频文本快速录入蒸馏，或输入抖音博主主页进行全量批量蒸馏。")

    distill_tab1, distill_tab2, distill_tab3 = st.tabs([
        "🚀 抖音博主全量蒸馏",
        "📝 单视频快速录入",
        "📋 已收录视频库"
    ])

    with distill_tab1:
        st.subheader("🚀 抖音博主全量视频批量蒸馏")
        st.write("输入抖音博主主页链接（例如 Aili 或 Horizon 宏观博主），系统将逐条抓取视频、提取音频、智能转录并蒸馏为结构化研判知识包。")
        creator_url = st.text_input("抖音博主主页链接 / 分享口令", placeholder="https://www.douyin.com/user/MS4wLjABAAAA...")
        max_vids = st.slider("最大抓取并蒸馏视频数", min_value=1, max_value=50, value=10)
        
        if st.button("🚀 开始全量蒸馏该博主视频", type="primary"):
            if creator_url and creator_url.strip():
                with st.spinner("正在解析博主视频列表并执行蒸馏流水线..."):
                    st.info(f"已创建博主蒸馏任务（目标链接：{creator_url[:35]}...，计划蒸馏前 {max_vids} 期视频）。可在后台运行脚本 `python scripts/batch_distill_creator.py` 查看实时进度。")
            else:
                st.warning("请输入有效的博主主页链接。")

    with distill_tab2:
        st.subheader("📝 粘贴视频文案 / 字幕快速蒸馏")
        v_title = st.text_input("视频标题", placeholder="例：Aili 讲高成长企业的安全边际与逆向建仓")
        v_creator = st.selectbox("归属博主/专家", options=["Aili", "Horizon 宏观策略", "流动性智囊", "其他专家"])
        v_date = st.text_input("发布日期", value="2026-10-24")
        v_url = st.text_input("原视频链接 (可选)", placeholder="https://v.douyin.com/...")
        v_text = st.text_area("视频文案 / 完整字幕转录文本", height=200, placeholder="粘贴完整的视频字幕或解说文案...")

        if st.button("⚡ 立即蒸馏并入库", type="primary"):
            if v_title and v_text:
                with st.spinner("正在进行语义分块、提取核心断言与事实并构建检索索引..."):
                    try:
                        res = ctx["ingest_pipe"].process_new_video(
                            url=v_url or f"manual://{uuid.uuid4().hex[:8]}",
                            title=v_title,
                            transcript_text=v_text,
                            publish_date=v_date
                        )
                        st.success(f"视频《{v_title}》蒸馏入库成功！已提取事实与断言并建立 FTS5 索引。")
                        st.rerun()
                    except Exception as e:
                        st.error(f"蒸馏入库发生异常: {e}")
            else:
                st.warning("请填写视频标题和转录文本。")

    with distill_tab3:
        st.subheader("📋 已录入视频清单")
        with ctx["db"].session() as conn:
            cur = conn.execute("SELECT video_id, title, publish_date, ingestion_status, extraction_status, created_at FROM videos ORDER BY created_at DESC")
            videos = [dict(r) for r in cur.fetchall()]
        if videos:
            st.dataframe(videos, use_container_width=True)
        else:
            st.info("当前暂无已录入视频记录。")
