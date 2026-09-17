import streamlit as st
import time
import random
import base64
import streamlit.components.v1 as components
from datetime import datetime
import sqlite3
import threading
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit_autorefresh import st_autorefresh
# Import our custom modules
import database
import ai_engine
import plotly.graph_objects as go  # 🎯 Sabse upar yeh import zaroor dalna!

# ------------------------------------------------------------------
# NAVIGATION HELPERS
# ------------------------------------------------------------------

def navigate_to(page_name):
    st.session_state.page = page_name
    if page_name == 'dashboard':
        st.session_state.dashboard_step = 'select_domain'
        st.session_state.quiz_data = None
    st.rerun()

def render_room_chat_sidebar():
    """Renders a live chat sidebar if the user is in a multiplayer room."""
    room_code = st.session_state.get('current_room_code')
    if not room_code:
        return 
        
    room_details = database.get_room_details(room_code)
    if not room_details:
        return
        
    host_username = room_details[0]
    username = st.session_state.username
    is_host = (username == host_username)
    
    # SMART AUTO-REFRESH: 3-sec auto-refresh in the Lobby and Results section !!
    is_live_test = (st.session_state.get('page') == 'dashboard' and st.session_state.get('dashboard_step') == 'test_execution')
    if not is_live_test:
        st_autorefresh(interval=3000, key="chat_auto_sync")
        
    with st.sidebar:
        st.markdown("### 💬 Live Room Chat")
        st.caption(f"Room Code: {room_code}")
        
        # 1. HOST CONTROLS 
        if is_host:
            current_perm = database.is_chat_allowed(room_code)
            new_perm = st.toggle("Allow Guests to Chat", value=current_perm)
            if new_perm != current_perm:
                database.update_chat_permission(room_code, new_perm)
                st.rerun()
        
        chat_allowed = database.is_chat_allowed(room_code)
        st.divider()
        
        # 2. CHAT HISTORY BOX (Scrollable)
        chat_box = st.container(height=350)
        msgs = database.get_room_chat(room_code)
        
        with chat_box:
            if not msgs:
                st.info("No messages yet. Start the banter!")
            for msg_user, msg_text, _ in msgs:
                ## TEXT FORMATTING: Main message text in <span style='font-size:0.85rem; font-weight:400;'>
                if msg_user == username:
                    st.markdown(f"<div style='text-align:right; background:rgba(59,130,246,0.15); padding:8px 12px; border-radius:12px; margin-bottom:6px; border: 1px solid rgba(59,130,246,0.3);'><span style='font-size:0.75rem; color:#94a3b8;'>You</span><br><span style='font-size:0.85rem; font-weight:400; color:#f8fafc;'>{msg_text}</span></div>", unsafe_allow_html=True)
                elif msg_user == host_username:
                    st.markdown(f"<div style='text-align:left; background:rgba(245,158,11,0.15); padding:8px 12px; border-radius:12px; margin-bottom:6px; border: 1px solid rgba(245,158,11,0.3);'><span style='font-size:0.75rem; color:#f59e0b;'>👑 {msg_user}</span><br><span style='font-size:0.85rem; font-weight:400; color:#f8fafc;'>{msg_text}</span></div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div style='text-align:left; background:rgba(255,255,255,0.05); padding:8px 12px; border-radius:12px; margin-bottom:6px; border: 1px solid rgba(255,255,255,0.1);'><span style='font-size:0.75rem; color:#94a3b8;'>{msg_user}</span><br><span style='font-size:0.85rem; font-weight:400; color:#f8fafc;'>{msg_text}</span></div>", unsafe_allow_html=True)
        
        # 3. CHAT INPUT FORM
        if is_host or chat_allowed:
            with st.form(key=f"chat_form_{len(msgs)}", clear_on_submit=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    new_msg = st.text_input("Type...", label_visibility="collapsed", placeholder="Message...")
                with c2:
                    submit = st.form_submit_button("Send")
                if submit and new_msg.strip():
                    database.add_chat_message(room_code, username, new_msg.strip())
                    st.rerun()
        else:
            st.error("Host has paused the chat")

def switch_to_signup():
    st.session_state.auth_mode = "Sign Up"
    st.session_state.login_failed = False
    st.session_state.signup_step = 'details'
    navigate_to('login')

def switch_to_login():
    st.session_state.auth_mode = "Login"
    st.session_state.login_failed = False
    navigate_to('login')

def get_avatar_url(username, style="micah"):
    """Generates a professional avatar using DiceBear API based on username"""
    # style='micah' gives clean, professional avatars. 'bottts' gives cool robots.
    return f"https://api.dicebear.com/7.x/{style}/svg?seed={username}&backgroundColor=transparent"

def get_avatar_presets(username):
    """Returns a dictionary of 10 premium 3D avatars"""
    return {
        "🌟 My Unique Avatar": get_avatar_url(username, style="micah"),
        "🤖 Cyber Bot": "https://api.dicebear.com/7.x/bottts/svg?seed=Cyber&backgroundColor=transparent",
        "🥷 Code Ninja": "https://api.dicebear.com/7.x/avataaars/svg?seed=Ninja&backgroundColor=transparent",
        "👩‍🚀 Space Explorer": "https://api.dicebear.com/7.x/adventurer/svg?seed=Explorer&backgroundColor=transparent",
        "🧙‍♂️ Tech Wizard": "https://api.dicebear.com/7.x/micah/svg?seed=Wizard&backgroundColor=transparent",
        "🦊 Clever Fox": "https://api.dicebear.com/7.x/fun-emoji/svg?seed=Fox&backgroundColor=transparent",
        "😎 Cool Hacker": "https://api.dicebear.com/7.x/lorelei/svg?seed=Hacker&backgroundColor=transparent",
        "🐼 Chill Panda": "https://api.dicebear.com/7.x/fun-emoji/svg?seed=Panda&backgroundColor=transparent",
        "👾 Retro Invader": "https://api.dicebear.com/7.x/pixel-art/svg?seed=Invader&backgroundColor=transparent",
        "🦸‍♀️ Super Coder": "https://api.dicebear.com/7.x/adventurer/svg?seed=Coder&backgroundColor=transparent"
    }

def get_image_base64(uploaded_file):
    return base64.b64encode(uploaded_file.getvalue()).decode()

def get_daily_tip():
    tips = [
        "Always clarify constraints before jumping into code during an interview.",
        "Think out loud. Interviewers want to see your problem-solving approach.",
        "In DBMS rounds, expect questions on Normalization and ACID properties.",
        "For Computer Networks, make sure you know the OSI model inside out.",
        "Don't rush to the optimal solution. Start with a brute-force approach first."
    ]
    day_of_year = datetime.now().timetuple().tm_yday
    return tips[day_of_year % len(tips)]

# ------------------------------------------------------------------
# DESIGN COLORS
# ------------------------------------------------------------------

DOMAIN_COLOR_MAP = {
    "Core CS Fundamentals": "#3b82f6",
    "English Grammar": "#f59e0b",
    "Quantitative Aptitude": "#7236FD",
    "Logical Reasoning": "#ec4899",
    "Database Management Systems (DBMS)": "#10b981",
    "Computer Networks": "#06b6d4",
    "Operating Systems": "#ef4444",
    "Cloud Computing": "#6366f1",
    "General": "#64748b",
}
_FALLBACK_PALETTE = ["#3b82f6", "#10b981", "#f59e0b", "#ec4899", "#8b5cf6", "#06b6d4", "#ef4444", "#6366f1"]

def get_domain_color(domain):
    if domain in DOMAIN_COLOR_MAP:
        return DOMAIN_COLOR_MAP[domain]
    return _FALLBACK_PALETTE[abs(hash(domain)) % len(_FALLBACK_PALETTE)]

def render_step_tracker(current_step):
    """Horizontal progress tracker shown at the top of the dashboard flow."""
    steps = [
        ("select_domain", "Domains"),
        ("configure_test", "Configure"),
        ("test_execution", "Test"),
        ("test_results", "Results"),
    ]
    step_keys = [s[0] for s in steps]
    current_idx = step_keys.index(current_step) if current_step in step_keys else 0

    html = "<div class='step-tracker'>"
    for i, (key, label) in enumerate(steps):
        if i < current_idx:
            circle_class, label_class, content = "done", "done", "✓"
        elif i == current_idx:
            circle_class, label_class, content = "active", "active", str(i + 1)
        else:
            circle_class, label_class, content = "", "", str(i + 1)

        html += f"<div class='step-item'>"
        html += f"<div class='step-circle {circle_class}'>{content}</div>"
        html += f"<div class='step-label {label_class}'>{label}</div>"
        html += "</div>"
        if i < len(steps) - 1:
            line_class = "done" if i < current_idx else ""
            html += f"<div class='step-line {line_class}'></div>"
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def render_xp_bar(total_points, rank):
    """Progress bar showing progress toward the next rank threshold."""
    thresholds = [0, 1000, 10000, 50000]
    labels = ["Beginner 🥉", "Intermediate 🥈", "Advanced 🥇", "Pro Hacker 💎"]

    if total_points >= thresholds[-1]:
        pct = 100
        next_label = "Max Rank Reached"
        remaining_text = "You've hit the top rank!"
    else:
        idx = 0
        for i, t in enumerate(thresholds):
            if total_points >= t:
                idx = i
        floor_val = thresholds[idx]
        ceil_val = thresholds[idx + 1]
        pct = int(((total_points - floor_val) / (ceil_val - floor_val)) * 100)
        next_label = labels[idx + 1]
        remaining_text = f"{ceil_val - total_points:,} XP to {next_label}"

    st.markdown(f"<div style='margin-top: 6px;'><div class='xp-bar-container'><div class='xp-bar-fill' style='width: {pct}%;'></div></div><p style='font-size: 0.8rem; color: #94a3b8 !important; margin-top: 6px;'>{remaining_text}</p></div>", unsafe_allow_html=True)

def hex_to_rgba(hex_color, alpha):
    hex_color = hex_color.lstrip('#')
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

def render_feature_card(icon, title, description, accent):
    icon_bg = hex_to_rgba(accent, 0.14)
    icon_border = hex_to_rgba(accent, 0.4)
    # NOTE: kept as a single-line f-string on purpose (no leading indentation) —
    # indented multi-line HTML inside st.markdown gets misread as a Markdown
    # code block by Streamlit's parser and breaks layout.
    st.markdown(f"<div class='feature-card' style='border-top: 3px solid {accent};'><div class='feature-icon-circle' style='background:{icon_bg}; border:1px solid {icon_border};'>{icon}</div><h3 style='font-size:1.1rem; margin-bottom:8px;'>{title}</h3><p style='color:#94a3b8 !important; font-size:0.9rem; line-height:1.5; margin-bottom:0;'>{description}</p></div>", unsafe_allow_html=True)

def render_cycling_text(items, cycle_seconds=2.2):
    """
    Isolated iframe (components.html) instead of st.markdown — this text swaps every couple of seconds via 
    JS, and running it in its own iframe means it can never collide with Streamlit's markdown parser or the
    app's CSS, which is what caused the earlier layout glitch.
    """
    items_js = str(items)
    html = f"""
    <div style="display:flex; align-items:center; justify-content:center; gap:6px;
                font-family:'Inter',sans-serif; font-size:16px; font-weight:600;
                color:#94a3b8; height:26px;">
      <span>Practice topics like</span>
      <span id="cycle-word" style="color:#60a5fa; min-width:190px; display:inline-block; transition:opacity 0.25s ease;"></span>
    </div>
    <script>
      const words = {items_js};
      let i = 0;
      const el = document.getElementById('cycle-word');
      function show() {{
        el.style.opacity = 0;
        setTimeout(function() {{
          el.textContent = words[i % words.length];
          el.style.opacity = 1;
          i++;
        }}, 200);
      }}
      show();
      setInterval(show, {int(cycle_seconds * 1000)});
    </script>
    """
    components.html(html, height=34)

# ------------------------------------------------------------------
# CSS
# ------------------------------------------------------------------

def inject_css():
    st.markdown("""
    <style>
        /* ============================================================
           DESIGN TOKENS
        ============================================================ */
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Sora:wght@600;700;800&display=swap');

        :root {
            --bg-void: #0a0e17;
            --glass-bg: rgba(255,255,255,0.035);
            --glass-bg-hover: rgba(255,255,255,0.065);
            --glass-border: rgba(255,255,255,0.09);
            --glass-border-hover: rgba(255,255,255,0.20);
            --text-primary: #f1f5f9;
            --text-muted: #94a3b8;
            --accent-blue: #3b82f6;
            --accent-green: #10b981;
            --accent-amber: #f59e0b;
            --accent-purple: #8b5cf6;
            --radius-lg: 22px;
            --radius-md: 16px;
            --radius-sm: 12px;
        }

        /* Apply Inter everywhere EXCEPT icon glyphs. Streamlit renders its icons
           (expander arrows, sidebar collapse arrow, password show/hide eye) as
           text ligatures like "arrow_right" through a special icon font, marked
           aria-hidden="true". Forcing * into Inter broke those ligatures, which
           is why raw words like "arrow_right" or "visibility" were showing up
           as overlapping text instead of icons. */
        html, body, p, div, h1, h2, h3, h4, h5, h6, span, label, input, button, textarea {
            font-family: 'Inter', sans-serif;
        }
        .display-font, .hero-title, .profile-header, .hc-hero-name, .hc-section-title {
            font-family: 'Sora', sans-serif !important;
        }

        /* Hide Streamlit's auto-generated anchor-link icon next to headings */
        [data-testid="stHeaderActionElements"] { display: none !important; }

        /* Main background — dark void with two soft accent glows + dot grid */
        .stApp {
            background:
                radial-gradient(circle at 12% -8%, rgba(59, 130, 246, 0.14), transparent 42%),
                radial-gradient(circle at 88% 4%, rgba(139, 92, 246, 0.10), transparent 38%),
                var(--bg-void) radial-gradient(rgba(255,255,255,0.035) 1px, transparent 1px) 0 0 / 22px 22px !important;
        }

        [data-testid="block-container"] { padding: 3.2rem 2.4rem 4rem 2.4rem; max-width: 1240px; }

        h1, h2, h3, h4, p, label, .stMarkdown { color: var(--text-primary) !important; }
        hr { border-color: rgba(255,255,255,0.08) !important; margin: 1.6rem 0 !important; }

        [data-testid="stMetricValue"] { color: var(--accent-blue) !important; font-size: 2.2rem !important; font-family: 'Sora', sans-serif !important; }
        [data-testid="stMetricLabel"] p { color: var(--text-muted) !important; font-size: 0.85rem !important; }

        /* 4. Sidebar */
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #0b0f19 0%, #0a0e17 100%) !important;
            border-right: 1px solid var(--glass-border) !important;
        }
        .hide-sidebar [data-testid="collapsedControl"] { display: none; }

        /* Native bordered containers (st.container(border=True)) -> glass
           cards everywhere they're used: profile, history, dashboard, home. */
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border: 1px solid var(--glass-border) !important;
            background: var(--glass-bg) !important;
            border-radius: var(--radius-md) !important;
            backdrop-filter: blur(14px);
        }

        /* Buttons — premium glass base everywhere, gradient for primary actions */
        .stButton > button, [data-testid="stFormSubmitButton"] > button {
            border-radius: 10px !important;
            font-weight: 600 !important;
            border: 1px solid rgba(255,255,255,0.12) !important;
            background: rgba(255,255,255,0.045) !important;
            color: var(--text-primary) !important;
            transition: border-color .2s ease, background .2s ease, transform .2s ease, box-shadow .2s ease !important;
        }
        .stButton > button:hover, [data-testid="stFormSubmitButton"] > button:hover {
            border-color: var(--accent-blue) !important;
            background: rgba(59, 130, 246, 0.14) !important;
            transform: translateY(-1px);
        }
        .stButton > button[kind="primary"], [data-testid="stFormSubmitButton"] > button[kind="primary"] {
            background: linear-gradient(135deg, #3b82f6, #6366f1) !important;
            border: none !important;
            box-shadow: 0 4px 16px rgba(59, 130, 246, 0.35) !important;
        }
        .stButton > button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {
            box-shadow: 0 6px 22px rgba(59, 130, 246, 0.5) !important;
            transform: translateY(-2px);
        }

        /* Inputs & selects */
        [data-testid="stTextInput"] input,
        [data-testid="stNumberInput"] input,
        [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
        [data-testid="stMultiSelect"] div[data-baseweb="select"] > div,
        [data-testid="stTextArea"] textarea {
            background: rgba(255,255,255,0.045) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: 10px !important;
            color: var(--text-primary) !important;
        }
        [data-testid="stTextInput"] input:focus, [data-testid="stNumberInput"] input:focus {
            border-color: var(--accent-blue) !important;
            box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.22) !important;
        }

        /* Alerts (info/success/warning/error) */
        [data-testid="stAlertContainer"] {
            border-radius: var(--radius-sm) !important;
            backdrop-filter: blur(6px);
        }

        /* Expanders (results breakdown, saved questions, history) */
        [data-testid="stExpander"] {
            background: var(--glass-bg) !important;
            border: 1px solid var(--glass-border) !important;
            border-radius: var(--radius-sm) !important;
        }

        /* Progress bar (live test progress) */
        [data-testid="stProgress"] > div > div > div {
            background: linear-gradient(90deg, var(--accent-blue), var(--accent-purple)) !important;
        }

        /* 5. Cards & Boxes */
        .feature-box, .question-box, .analytics-box {
            background-color: var(--glass-bg);
            padding: 26px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--glass-border) !important;
            text-align: center;
            transition: transform 0.2s, border-color 0.2s, background-color 0.2s;
            height: 100%;
        }
        .feature-box:hover {
            transform: translateY(-3px);
            border-color: var(--accent-blue) !important;
            background-color: var(--glass-bg-hover);
        }
        .question-box { text-align: left !important; padding: 28px 30px; }
        .analytics-box h4 { color: var(--text-muted) !important; font-weight: 500; font-size: 0.82rem; margin-bottom: 8px; }
        .analytics-box h2 { margin: 0; font-family: 'Sora', sans-serif; }

        /* Landing page feature cards */
        .feature-card {
            background-color: rgba(255, 255, 255, 0.04);
            border: 1px solid rgba(255, 255, 255, 0.09);
            border-radius: 14px;
            padding: 30px 22px;
            text-align: center;
            height: 100%;
            transition: transform 0.22s ease, border-color 0.22s ease, background-color 0.22s ease;
        }
        .feature-card:hover {
            transform: translateY(-4px);
            background-color: rgba(255, 255, 255, 0.06);
            border-color: rgba(255, 255, 255, 0.2);
        }
        .feature-icon-circle {
            width: 54px; height: 54px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            margin: 0 auto 16px auto;
            font-size: 1.5rem;
        }

        /* 6. Radio buttons background (quiz options) */
        .stRadio > div {
            background-color: rgba(255,255,255,0.03);
            padding: 20px;
            border-radius: var(--radius-sm);
            border: 1px solid var(--glass-border);
        }

        /* 7. Step Tracker (dashboard flow) */
        .step-tracker {
            display: flex; align-items: center; justify-content: center;
            margin: 6px 0 36px 0; flex-wrap: wrap;
        }
        .step-item { display: flex; align-items: center; }
        .step-circle {
            width: 34px; height: 34px; border-radius: 50%;
            display: flex; align-items: center; justify-content: center;
            font-weight: 700; font-size: 0.85rem;
            border: 2px solid #334155; color: #94a3b8; background: #0f172a;
            flex-shrink: 0;
        }
        .step-circle.active {
            border-color: var(--accent-blue); color: #fff; background: var(--accent-blue);
            box-shadow: 0 0 14px rgba(59, 130, 246, 0.6);
        }
        .step-circle.done { border-color: var(--accent-green); color: #fff; background: var(--accent-green); }
        .step-label { margin: 0 10px 0 8px; font-size: 0.82rem; color: #94a3b8 !important; }
        .step-label.active { color: #fff !important; font-weight: 700; }
        .step-label.done { color: var(--accent-green) !important; }
        .step-line { width: 40px; height: 2px; background: #334155; margin: 0 2px; }
        .step-line.done { background: var(--accent-green); }

        /* 8. XP Bar (profile page) */
        .xp-bar-container {
            background: rgba(255, 255, 255, 0.08);
            border-radius: 10px; height: 14px; width: 100%; overflow: hidden;
        }
        .xp-bar-fill {
            height: 100%; border-radius: 10px;
            background: linear-gradient(90deg, #3b82f6, #8b5cf6);
            transition: width 0.4s ease;
        }

        /* 9. Room code badge (challenge lobby) */
        .room-code-badge {
            display: inline-block;
            font-family: 'Courier New', monospace;
            font-size: 1.9rem; font-weight: 800; letter-spacing: 8px;
            background: rgba(59, 130, 246, 0.12);
            border: 2px dashed #3b82f6;
            padding: 10px 26px; border-radius: 12px;
            color: #60a5fa !important;
        }

        /* 10. Participant chips */
        .participant-chip {
            display: flex; align-items: center; gap: 10px;
            background: rgba(255, 255, 255, 0.05);
            padding: 9px 14px; border-radius: 30px;
            margin-bottom: 8px;
            border: 1px solid rgba(255, 255, 255, 0.08);
        }
        .chip-avatar {
            width: 26px; height: 26px; border-radius: 50%;
            background: #3b82f6;
            display: flex; align-items: center; justify-content: center;
            font-size: 0.8rem; flex-shrink: 0;
        }
        .chip-host { background: #f59e0b; }
        .chip-status { margin-left: auto; font-size: 0.78rem; color: #94a3b8 !important; }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.page == 'login':
        st.markdown("""
        <style>
            /* THIS IS THE BOX-WIDTH CONTROL. All 4 elements (Sign In, Create
               Account, the email box, the password box) just stretch to fill
               whatever width their parent container is. Capping the parent
               container here shrinks all 4 together.
               max-width below = the actual width of the whole login card.
               Lower it (e.g. 340px) for a narrower card, raise it for wider. */
            [data-testid="block-container"],
            [data-testid="stMainBlockContainer"],
            [data-testid="stAppViewBlockContainer"] {
                background: rgba(15, 23, 42, 0.7) !important;
                backdrop-filter: blur(16px) !important;
                border-radius: 20px !important;
                padding: 1.7rem 2rem !important;
                margin: 3vh auto 0 auto !important;
                max-width: 900px !important;
                box-shadow: 0 10px 40px rgba(0, 0, 0, 0.9) !important;
                border: 1px solid rgba(255, 255, 255, 0.15) !important;
            }
            [data-testid="stTextInput"] input {
                border-radius: 10px;
                border: 1px solid #4a5568;
                background-color: rgba(0, 0, 0, 0.4);
                color: white;
                padding: 6px 12px !important;
                transition: box-shadow 0.2s, border-color 0.2s;
            }
            /* Tighten vertical rhythm between stacked fields/buttons on the login card */
            [data-testid="stVerticalBlock"] .element-container { margin-bottom: 0.35rem !important; }
            [data-testid="stTextInput"] input:focus {
                border-color: #3b82f6 !important;
                box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.25) !important;
            }
            /* OTP field (max_chars=6 -> maxlength="6") gets special large styling */
            [data-testid="stTextInput"] input[maxlength="6"] {
                text-align: center;
                font-size: 1.6rem;
                letter-spacing: 12px;
                font-weight: 700;
                color: #60a5fa !important;
            }
            [data-testid="stTextInput"] { margin-bottom: -6px; }
            .stButton > button {
                border-radius: 10px;
                background-color: #3b82f6;
                color: white;
                border: none;
                transition: 0.3s;
                font-weight: bold;
            }
            .stButton > button:hover {
                background-color: #2563eb;
                box-shadow: 0 0 14px rgba(59, 130, 246, 0.5);
            }
            .auth-step-pill-wrap { text-align: center; margin: 4px 0 18px 0; }
            .auth-step-pill {
                display: inline-block;
                padding: 4px 14px;
                border-radius: 20px;
                font-size: 0.75rem;
                font-weight: 700;
                background: rgba(59, 130, 246, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.4);
                color: #60a5fa !important;
            }
        </style>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <style>
            .hero-title { font-size: 4rem; font-weight: 800; text-align: center; background: -webkit-linear-gradient(45deg, #3b82f6, #8b5cf6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0px; letter-spacing: -0.01em; }
            .profile-header { font-size: 3rem; font-weight: 700; background: -webkit-linear-gradient(45deg, #10b981, #3b82f6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
        </style>
        """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# LANDING PAGE (redesigned bento grid)
# ------------------------------------------------------------------

FEATURE_CARDS = [
    ("🧠", "Generative AI Core", "Endless unique questions powered by advanced LLMs. You will never take the same test twice.", "#3b82f6"),
    ("⏳", "Real Exam Pressure", "Customizable per-question countdown timers simulating placement exams.", "#f59e0b"),
    ("📊", "Instant Analytics", "Immediate feedback and detailed step-by-step explanations the moment a test concludes.", "#10b981"),
    ("🎯", "Custom Domains", "Practice Aptitude, core Computer Science, or any custom tech stack you want to learn.", "#ec4899"),
    ("📈", "Progress Tracking", "Monitor your daily streaks, earn XP, and build a strong professional profile.", "#8b5cf6"),
    ("💼", "Interview Ready", "Architected specifically to help engineering students clear technical rounds and campus placements.", "#06b6d4"),
]

def get_real_recent_activity(username):
    conn = database.get_connection()
    c = conn.cursor()
    activities = []
    
    # 1. Fetch Multiplayer Results (Challenge Mode)
    try:
        c.execute("SELECT room_code, score, timestamp FROM room_results WHERE username = ? ORDER BY timestamp DESC LIMIT 2", (username,))
        for row in c.fetchall():
            room_code, score, time_str = row
            # Live rank is being calculated for a room
            c.execute("SELECT username FROM room_results WHERE room_code = ? ORDER BY score DESC, time_taken ASC", (room_code,))
            ranks = [r[0] for r in c.fetchall()]
            my_rank = ranks.index(username) + 1 if username in ranks else '-'
            
            activities.append((time_str, f"⚔️ Ranked <b>#{my_rank}</b> in Room {room_code} <br><span style='color:#94a3b8; font-size:12px;'>Score: {score} XP</span>"))
    except Exception: 
        pass
    
    # 2. Fetch Solo Test History 
    try:
#######        # Note: Agar tumhare DB mein column names alag hain (jaise domain/topic), toh unhe yahan change kar lena
        c.execute("SELECT domain, score, timestamp FROM history WHERE username = ? ORDER BY timestamp DESC LIMIT 2", (username,))
        for row in c.fetchall():
            topic, score, time_str = row
            activities.append((time_str, f"🎯 Scored <b>{score}</b> in {topic} <br><span style='color:#94a3b8; font-size:12px;'>Solo Assessment</span>"))
    except Exception: 
        pass
        
    conn.close()
    
    # Sort by timestamp (Latest first) and return only top 3
    activities.sort(key=lambda x: x[0], reverse=True)
    return [act[1] for act in activities[:3]]

def page_home():
    username = st.session_state.username
    avatar_url = get_avatar_url(username, style="micah")
    total_points, tests_completed = database.get_user_stats(username)

    if total_points < 1000: rank = "Beginner 🥉"
    elif total_points < 10000: rank = "Intermediate 🥈"
    elif total_points < 50000: rank = "Advanced 🥇"
    else: rank = "Pro Hacker 💎"

    hour = datetime.now().hour
    if hour < 12: greeting_word = "Good morning"
    elif hour < 17: greeting_word = "Good afternoon"
    else: greeting_word = "Good evening"

    # ------------------------------------------------------------------
    # Real topic-wise performance, built from actual test history.
    # Each row in test_history stores one accuracy % (already 0-100) for
    # a whole session's domains — we attribute that accuracy to every
    # domain that appeared in that session, then average per domain across
    # all sessions. No schema changes, just aggregation over existing data.
    # ------------------------------------------------------------------
    history_rows = database.get_user_history(username)
    topic_scores = {}
    for row in history_rows:
        _, domains_str, _attempted, _total, _score, accuracy = row
        if not domains_str:
            continue
        for d in [t.strip() for t in domains_str.split(",") if t.strip()]:
            topic_scores.setdefault(d, []).append(accuracy)
    topic_avg = {d: sum(v) / len(v) for d, v in topic_scores.items()}
    ranked_topics = sorted(topic_avg.items(), key=lambda x: x[1], reverse=True)

    # ------------------------------------------------------------------
    # Page-local CSS: the hero band + "Choose Your Path" cards.
    # Everything shared across pages (buttons, inputs, bordered containers)
    # already comes from inject_css() — this block only covers markup
    # that's unique to this page's layout.
    # ------------------------------------------------------------------
    st.markdown("""
    <style>
    .hc-hero {
        background: linear-gradient(135deg, rgba(59,130,246,0.12), rgba(139,92,246,0.05) 60%);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 22px;
        padding: 32px 38px;
        position: relative;
        overflow: hidden;
        margin-bottom: 30px;
    }
    .hc-hero::before {
        content: "";
        position: absolute; top: 0; left: 0; right: 0; height: 3px;
        background: linear-gradient(90deg, #3b82f6, #8b5cf6, #ec4899);
    }
    .hc-hero-row { display: flex; align-items: center; gap: 24px; flex-wrap: wrap; }
    .hc-avatar-ring {
        width: 84px; height: 84px; border-radius: 50%; flex-shrink: 0;
        padding: 3px;
        background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    }
    .hc-avatar-ring img { width: 100%; height: 100%; border-radius: 50%; display: block; background: #0f172a; }
    .hc-hero-text { flex: 1; min-width: 220px; }
    .hc-hero-name { font-size: 1.9rem; font-weight: 700; margin: 0; line-height: 1.2; }
    .hc-hero-sub { color: #94a3b8; font-size: 0.98rem; margin-top: 4px; }
    .hc-stat-row { display: flex; gap: 12px; flex-wrap: wrap; }
    .hc-stat-pill {
        background: rgba(255,255,255,0.05);
        border: 1px solid rgba(255,255,255,0.09);
        border-radius: 14px;
        padding: 10px 18px;
        text-align: center;
        min-width: 96px;
    }
    .hc-stat-pill .val { font-family: 'Sora', sans-serif; font-size: 1.2rem; font-weight: 700; color: #f1f5f9; line-height: 1.15; }
    .hc-stat-pill .lbl { font-size: 0.68rem; color: #94a3b8; margin-top: 3px; letter-spacing: 0.01em; }

    .hc-section-title {
        font-family: 'Sora', sans-serif; font-weight: 700; font-size: 1.25rem;
        margin: 4px 0 16px 2px;
    }

    /* The 4 "Choose Your Path" cards use the same invisible-marker +
       adjacent-sibling trick as the original (Streamlit gives buttons no
       class hook of their own), just re-themed to match the new tokens. */
    div[data-testid="element-container"]:has(.hc-path-marker) + div[data-testid="element-container"] button {
        height: 172px !important;
        white-space: break-spaces !important;
        text-align: left !important;
        border-radius: 16px !important;
        padding: 20px 22px !important;
        width: 100% !important;
        display: flex !important;
        align-items: flex-start !important;
        justify-content: flex-start !important;
        transition: all 0.25s ease !important;
    }
    div[data-testid="element-container"]:has(.hc-path-marker) + div[data-testid="element-container"] button p {
        font-size: 1.05rem !important;
        line-height: 1.55 !important;
        margin: 0 !important;
    }
    div[data-testid="element-container"]:has(.hc-path-blue) + div[data-testid="element-container"] button {
        background: rgba(59,130,246,0.06) !important; border: 1px solid rgba(59,130,246,0.22) !important; border-top: 3px solid #3b82f6 !important;
    }
    div[data-testid="element-container"]:has(.hc-path-blue) + div[data-testid="element-container"] button:hover {
        background: rgba(59,130,246,0.16) !important; transform: translateY(-6px); box-shadow: 0 12px 24px rgba(59,130,246,0.22) !important;
    }
    div[data-testid="element-container"]:has(.hc-path-green) + div[data-testid="element-container"] button {
        background: rgba(16,185,129,0.06) !important; border: 1px solid rgba(16,185,129,0.22) !important; border-top: 3px solid #10b981 !important;
    }
    div[data-testid="element-container"]:has(.hc-path-green) + div[data-testid="element-container"] button:hover {
        background: rgba(16,185,129,0.16) !important; transform: translateY(-6px); box-shadow: 0 12px 24px rgba(16,185,129,0.22) !important;
    }
    div[data-testid="element-container"]:has(.hc-path-orange) + div[data-testid="element-container"] button {
        background: rgba(245,158,11,0.06) !important; border: 1px solid rgba(245,158,11,0.22) !important; border-top: 3px solid #f59e0b !important;
    }
    div[data-testid="element-container"]:has(.hc-path-orange) + div[data-testid="element-container"] button:hover {
        background: rgba(245,158,11,0.16) !important; transform: translateY(-6px); box-shadow: 0 12px 24px rgba(245,158,11,0.22) !important;
    }
    div[data-testid="element-container"]:has(.hc-path-purple) + div[data-testid="element-container"] button {
        background: rgba(139,92,246,0.06) !important; border: 1px solid rgba(139,92,246,0.22) !important; border-top: 3px solid #8b5cf6 !important;
    }
    div[data-testid="element-container"]:has(.hc-path-purple) + div[data-testid="element-container"] button:hover {
        background: rgba(139,92,246,0.16) !important; transform: translateY(-6px); box-shadow: 0 12px 24px rgba(139,92,246,0.22) !important;
    }
    .hc-path-marker { display: none !important; }
    </style>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 1. HERO — avatar, greeting, quick stats. Pure display content, so
    #    it's one flat HTML block (no live Streamlit widgets inside it).
    # ------------------------------------------------------------------
    st.markdown(f"""
    <div class="hc-hero">
        <div class="hc-hero-row">
            <div class="hc-avatar-ring"><img src="{avatar_url}"></div>
            <div class="hc-hero-text">
                <p class="hc-hero-name">{greeting_word}, {username} ⚡</p>
                <p class="hc-hero-sub">Your AI Interview Command Center</p>
            </div>
            <div class="hc-stat-row">
                <div class="hc-stat-pill"><div class="val">{total_points:,}</div><div class="lbl">TOTAL XP</div></div>
                <div class="hc-stat-pill"><div class="val">{tests_completed}</div><div class="lbl">TESTS DONE</div></div>
                <div class="hc-stat-pill"><div class="val" style="font-size:0.95rem;">{rank}</div><div class="lbl">RANK</div></div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 2. SMART FOCUS — replaces the old static "Preparation Target" +
    #    fake "Resume" button with something that actually uses your data:
    #    your weakest topic (from the aggregation above) with a one-click
    #    shortcut straight into a configured test for exactly that topic.
    #    If there's no history yet, it falls back to a first-test nudge.
    # ------------------------------------------------------------------
    with st.container(border=True):
        if ranked_topics:
            weak_topic, weak_score = ranked_topics[-1]
            strong_topic, strong_score = ranked_topics[0]
            weak_color = get_domain_color(weak_topic)
            fc1, fc2 = st.columns([3, 1])
            with fc1:
                st.markdown(f"""
                <p class='hc-section-title' style='margin-bottom:5px;'>🎯 Smart Focus</p>
                <p style='color:#94a3b8; margin:0; line-height:1.5;'>
                    Your weakest area right now is
                    <b style='color:{weak_color};'>{weak_topic}</b> at
                    <b style='color:{weak_color};'>{weak_score:.0f}%</b> average accuracy.
                    {"Your strongest is <b style='color:" + get_domain_color(strong_topic) + ";'>" + strong_topic + "</b> at " + f"{strong_score:.0f}%." if strong_topic != weak_topic else ""}
                    A focused round here will move your overall readiness the most.
                </p>
                """, unsafe_allow_html=True)
            with fc2:
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                if st.button("Practice This ➡️", type="primary", use_container_width=True, key="smart_focus_btn"):
                    st.session_state.selected_domains = [weak_topic]
                    st.session_state.dashboard_step = 'configure_test'
                    st.session_state.page = 'dashboard'
                    st.rerun()
        else:
            fc1, fc2 = st.columns([3, 1])
            with fc1:
                st.markdown("""
                <p class='hc-section-title' style='margin-bottom:4px;'>🚀 Get Your First Read</p>
                <p style='color:#94a3b8; margin:0; line-height:1.5;'>
                    Take one mock assessment and this space turns into a live breakdown of your
                    strengths and weak spots by topic — automatically, from your real results.
                </p>
                """, unsafe_allow_html=True)
            with fc2:
                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)
                if st.button("Start a Test ➡️", type="primary", use_container_width=True, key="smart_focus_btn"):
                    st.session_state.page = 'dashboard'
                    st.rerun()

    st.markdown("<div style='height: 26px;'></div>", unsafe_allow_html=True)

    # ------------------------------------------------------------------
    # 3. THE MAIN PATHS (identical 4 buttons/keys/destinations as before)
    # ------------------------------------------------------------------
    st.markdown("<p class='hc-section-title'>🧭 Choose Your Path</p>", unsafe_allow_html=True)
    card_col1, card_col2, card_col3, card_col4 = st.columns(4)

    with card_col1:
        st.markdown('<div class="hc-path-marker hc-path-blue"></div>', unsafe_allow_html=True)
        if st.button("🎯 Mock Assessments\nSolo AI Training", key="btn_solo", use_container_width=True):
            st.session_state.page = 'dashboard'
            st.rerun()

    with card_col2:
        st.markdown('<div class="hc-path-marker hc-path-green"></div>', unsafe_allow_html=True)
        if st.button("⚔️ Live Contests\nMultiplayer Arena", key="btn_multi", use_container_width=True):
            st.session_state.page = 'challenge'
            st.rerun()

    with card_col3:
        st.markdown('<div class="hc-path-marker hc-path-orange"></div>', unsafe_allow_html=True)
        if st.button("📚 Knowledge Base\nNotes & Vault", key="btn_vault", use_container_width=True):
            st.session_state.page = 'vault'
            st.rerun()

    with card_col4:
        st.markdown('<div class="hc-path-marker hc-path-purple"></div>', unsafe_allow_html=True)
        if st.button("📊 Performance\nAnalytics & Ranks", key="btn_perf", use_container_width=True):
            st.session_state.page = 'profile'
            st.rerun()

    # ------------------------------------------------------------------
    # 4. TOPIC PERFORMANCE & REAL ACTIVITY.
    #    The old panel was a hardcoded radar chart with fake numbers. This
    #    is a real bar chart built from the same topic_avg aggregation
    #    above: x = topic, y = your average accuracy on it (already on a
    #    0-100 scale regardless of how many questions/marks each test had,
    #    so different-sized tests compare fairly). Bars are ranked strongest
    #    to weakest, colour-coded, and labelled with your rank (#1, #2...)
    #    among your own topics — the activity feed logic is untouched.
    # ------------------------------------------------------------------
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    r_col1, r_col2 = st.columns([2, 1])

    with r_col1:
        with st.container(height=340, border=True):
            st.markdown("<p class='hc-section-title' style='margin-bottom:0;'>📊 Topic Performance</p>", unsafe_allow_html=True)

            if not ranked_topics:
                st.markdown("<div style='height:40px;'></div>", unsafe_allow_html=True)
                st.info("Take a mock assessment to unlock your topic-wise performance breakdown here.")
            else:
                topics = [t for t, _ in ranked_topics]
                scores = [round(s, 1) for _, s in ranked_topics]
                colors = [get_domain_color(t) for t in topics]
                rank_labels = [f"#{i+1}" for i in range(len(topics))]

                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=topics,
                    y=scores,
                    marker=dict(color=colors, line=dict(width=0)),
                    text=[f"{s:.0f}%" for s in scores],
                    textposition='outside',
                    customdata=rank_labels,
                    hovertemplate="%{x}<br>Avg. Accuracy: %{y:.0f}%<br>Your Rank: %{customdata}<extra></extra>"
                ))
                fig.update_layout(
                    yaxis=dict(range=[0, 110], gridcolor='rgba(255,255,255,0.08)', color='rgba(255,255,255,0.6)', title="Avg. Accuracy (out of 100)"),
                    xaxis=dict(color='white', tickfont=dict(size=11)),
                    showlegend=False,
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    margin=dict(l=10, r=10, t=10, b=10),
                    height=230
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

    with r_col2:
        with st.container(height=340, border=True):
            st.markdown("<p class='hc-section-title'>Recent Activity</p>", unsafe_allow_html=True)
            st.divider()

            try:
                activities = get_real_recent_activity(username)
                if not activities:
                    st.info("No activity yet. Start your first Mock Assessment!")
                else:
                    for act in activities:
                        st.markdown(f"<div style='background: rgba(255,255,255,0.05); padding: 12px; border-radius: 8px; margin-bottom: 12px; border-left: 4px solid #3b82f6; font-size: 0.9rem;'>{act}</div>", unsafe_allow_html=True)
            except Exception:
                st.info("No activity yet. Start your first Mock Assessment!")

def page_landing():
    st.markdown("<div class='hero-title'>AI Interview Simulator</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; font-size: 1.35rem; color: #cbd5e1 !important; line-height: 1.5; margin: 14px auto 6px auto; max-width: 640px;'>Master your aptitude and technical rounds with dynamic, AI-generated mock tests.</p>", unsafe_allow_html=True)

    render_cycling_text(["DBMS", "Computer Networks", "Quantitative Aptitude", "Operating Systems", "Cloud Computing"])

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Get Started Now", use_container_width=True, type="primary"): switch_to_signup()
        if st.button("Already have an account? Login", use_container_width=True): switch_to_login()
    st.write("---")

    st.markdown("<h2 style='text-align: center; font-family: \"Sora\", sans-serif; margin-bottom: 8px;'>Why Practice Here?</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; margin-bottom: 38px;'>Everything you need to walk into your next technical round with confidence.</p>", unsafe_allow_html=True)

    # 🎯 CSS FOR 100% EQUAL HEIGHT CARDS (Main Fix)
    st.markdown("""
    <style>
    .fixed-feature-card {
        background: rgba(255, 255, 255, 0.035);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 28px 20px;
        height: 250px !important; /* 🎯 YAHAN HEIGHT STRICTLY FIX KAR DI HAI */
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        transition: transform 0.28s ease, box-shadow 0.28s ease, border-color 0.28s ease;
        margin-bottom: 18px;
    }
    .fixed-feature-card:hover {
        transform: translateY(-6px);
        box-shadow: 0 16px 32px rgba(0,0,0,0.45);
        border-color: rgba(255,255,255,0.18);
    }
    .icon-circle {
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 50%;
        width: 56px;
        height: 56px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.6rem;
        margin-bottom: 16px;
    }
    </style>
    """, unsafe_allow_html=True)

    # Uniform 3x2 grid — same card size for all six, differentiated only by accent color
    row1 = st.columns(3)
    for col, (icon, title, desc, accent) in zip(row1, FEATURE_CARDS[:3]):
        with col:
            # 🎯 Pura card HTML se render kar diya directly, taaki size na hile aur tumhara color apply ho jaye
            st.markdown(f"""
            <div class="fixed-feature-card" style="border-top: 4px solid {accent};">
                <div class="icon-circle">{icon}</div>
                <h4 style="margin-bottom: 12px; color: white; font-family: 'Sora', sans-serif;">{title}</h4>
                <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

    st.write("<br>", unsafe_allow_html=True)

    row2 = st.columns(3)
    for col, (icon, title, desc, accent) in zip(row2, FEATURE_CARDS[3:]):
        with col:
            st.markdown(f"""
            <div class="fixed-feature-card" style="border-top: 4px solid {accent};">
                <div class="icon-circle">{icon}</div>
                <h4 style="margin-bottom: 12px; color: white; font-family: 'Sora', sans-serif;">{title}</h4>
                <p style="font-size: 0.85rem; color: #94a3b8; line-height: 1.5;">{desc}</p>
            </div>
            """, unsafe_allow_html=True)

# ------------------------------------------------------------------
# LOGIN / SIGNUP PAGE
# ------------------------------------------------------------------

def page_login():
    col_back, _ = st.columns([0.18, 0.82])
    with col_back:
        if st.button("⬅️", help="Back to Home"):
            navigate_to('landing')

    st.markdown("<h2 style='text-align: center;'>Welcome to AI-QuizGen</h2>", unsafe_allow_html=True)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔑 Sign In", use_container_width=True):
            st.session_state.auth_mode = "Login"
            st.rerun()
    with col2:
        if st.button("📝 Create Account", use_container_width=True):
            st.session_state.auth_mode = "Sign Up"
            st.session_state.signup_step = 'details'
            st.rerun()

    st.markdown(f"<h3 style='text-align: center; margin-top: 15px;'>{st.session_state.auth_mode}</h3>", unsafe_allow_html=True)

    if st.session_state.auth_mode == "Sign Up":
        step_label = "Step 1 of 2 — Your Details" if st.session_state.signup_step == 'details' else "Step 2 of 2 — Verify Email"
        st.markdown(f"<div class='auth-step-pill-wrap'><span class='auth-step-pill'>{step_label}</span></div>", unsafe_allow_html=True)

        if st.session_state.signup_step == 'details':
            email = st.text_input("Email Address")
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            confirm_password = st.text_input("Confirm Password", type='password')

            if st.button("Send Verification OTP", use_container_width=True):
                if not email or not username or not password or not confirm_password:
                    st.warning("Please fill in all fields.")
                elif password != confirm_password:
                    st.warning("Passwords must match.")
                else:
                    conn = database.get_connection()
                    c = conn.cursor()
                    c.execute("SELECT * FROM users WHERE username = ?", (username,))
                    if c.fetchone():
                        st.error("Username already exists.")
                    else:
                        st.session_state.generated_otp = str(random.randint(100000, 999999))
                        st.session_state.temp_signup_data = {'email': email, 'username': username, 'password': password}
                        st.session_state.signup_step = 'otp'
                        st.rerun()
                    conn.close()

        elif st.session_state.signup_step == 'otp':
            st.info(f"An OTP has been sent to {st.session_state.temp_signup_data['email']}")
            st.warning(f"MOCK EMAIL ALERT: For testing purposes, your OTP is: {st.session_state.generated_otp}")
            user_otp = st.text_input("Enter 6-digit OTP", max_chars=6, label_visibility="collapsed", placeholder="------")

            if st.button("Verify and Create Account", use_container_width=True):
                if user_otp == st.session_state.generated_otp:
                    conn = database.get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO users (email, username, password, profile_pic) VALUES (?, ?, ?, ?)",
                              (st.session_state.temp_signup_data['email'], st.session_state.temp_signup_data['username'], st.session_state.temp_signup_data['password'], "👨‍💻"))
                    conn.commit()
                    conn.close()
                    st.success("Account created successfully! Redirecting to Login...")
                    time.sleep(1.5)
                    st.session_state.auth_mode = "Login"
                    st.session_state.signup_step = 'details'
                    st.rerun()
                else:
                    st.error("Invalid OTP. Please try again.")

    elif st.session_state.auth_mode == "Login":
        login_id = st.text_input("Email or Username")
        password = st.text_input("Password", type='password')

        if st.button("Proceed to Login", use_container_width=True):
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT username FROM users WHERE (username = ? OR email = ?) AND password = ?", (login_id, login_id, password))
            data = c.fetchone()
            conn.close()

            if data:
                st.session_state.username = data[0]
                time.sleep(0.5)
                navigate_to('home')
            else:
                st.error("Invalid Username/Email or Password")

def page_vault():
    st.markdown("<div style='display:flex; align-items:center; gap:12px;'><span style='font-size:2.4rem;'>📚</span><div class='profile-header' style='font-size: 3rem;'>Knowledge Base</div></div>", unsafe_allow_html=True)
    st.write("Every question you've bookmarked, the notes you've written on them, and your full test history — all in one place.")

    tab_saved, tab_history = st.tabs(["🔖 Bookmarks & Notes", "📜 Test History"])
    with tab_saved:
        page_saved_questions()
    with tab_history:
        page_history()
        
# ------------------------------------------------------------------
# DASHBOARD
# ------------------------------------------------------------------

def page_dashboard():
    # Helper functions call
    try:
        render_room_chat_sidebar()
        render_step_tracker(st.session_state.dashboard_step)
    except Exception:
        pass

    import time
    import threading
    import streamlit.components.v1 as components
    from streamlit.runtime.scriptrunner import add_script_run_ctx

    # --- STEP 1: SELECT DOMAIN & UPLOAD MATERIAL ---
    if st.session_state.dashboard_step == 'select_domain':
        col_welcome, col_qod = st.columns([2, 1])
        with col_welcome:
            st.markdown(f"<h2>Welcome, {st.session_state.username} ✨</h2>", unsafe_allow_html=True)
            st.write("Ready to level up? Select single or multiple domains to start a comprehensive test session.")
        with col_qod:
            try:
                st.info(f"💡 **Daily Tip:** {get_daily_tip()}")
            except Exception:
                pass

        st.divider()
        st.markdown("### Step 1: Select Your Test Domains OR Upload Material")

        predefined_domains = [
            "Core CS Fundamentals", "English Grammar", "Quantitative Aptitude",
            "Logical Reasoning", "Database Management Systems (DBMS)",
            "Computer Networks", "Operating Systems", "Cloud Computing"
        ]

        all_options = predefined_domains + [t for t in st.session_state.get('custom_topics', []) if t not in predefined_domains]

        current_selections = st.multiselect(
            "Select predefined topics:",
            options=all_options,
            default=[d for d in st.session_state.selected_domains if d in all_options]
        )

        def add_domain_quick(domain_list):
            for d in domain_list:
                if d not in st.session_state.get('custom_topics', []) and d not in predefined_domains:
                    if 'custom_topics' not in st.session_state: st.session_state.custom_topics = []
                    st.session_state.custom_topics.append(d)
                if d not in current_selections:
                    current_selections.append(d)

        st.write("<br><b>Or use Quick Add Topics:</b>", unsafe_allow_html=True)
        d1, d2, d3, d4 = st.columns(4)
        with d1:
            if st.button("🧠 Aptitude & Logic", use_container_width=True): add_domain_quick(["Quantitative Aptitude"]); st.session_state.selected_domains = current_selections; st.rerun()
        with d2:
            if st.button("🌐 Computer Networks", use_container_width=True): add_domain_quick(["Computer Networks"]); st.session_state.selected_domains = current_selections; st.rerun()
        with d3:
            if st.button("💾 DBMS Core", use_container_width=True): add_domain_quick(["Database Management Systems (DBMS)"]); st.session_state.selected_domains = current_selections; st.rerun()
        with d4:
            if st.button("📝 Verbal Ability", use_container_width=True): add_domain_quick(["English Grammar"]); st.session_state.selected_domains = current_selections; st.rerun()

        st.write("<br>", unsafe_allow_html=True)
        col_cust, col_btn = st.columns([4, 1])
        with col_cust:
            custom_domain_input = st.text_input("Add Custom Topics (comma-separated, e.g., SQL, ReactJS):", key="custom_domain_input")
        with col_btn:
            st.write("<br>", unsafe_allow_html=True)
            if st.button("Add Custom Topic(s)", use_container_width=True) and custom_domain_input:
                new_topics = [t.strip() for t in custom_domain_input.split(",") if t.strip()]
                add_domain_quick(new_topics)
                st.session_state.selected_domains = current_selections
                st.rerun()

        st.session_state.selected_domains = current_selections

        # 🎯 MOVED THE RAG/FILE UPLOAD FEATURE HERE TO STEP 1
        st.write("<br>", unsafe_allow_html=True)
        st.subheader("📎 Upload Custom Reference Material (Optional)")
        st.caption("Upload a syllabus, notes, or documentation. If you upload a file, you can skip selecting domains above!")
        
        uploaded_file = st.file_uploader("Upload PDF, DOCX, or TXT file", type=["pdf", "docx", "txt"])
        
        if uploaded_file is not None:
            with st.spinner("Extracting text from your file..."):
                try:
                    if uploaded_file.name.endswith('.pdf'):
                        import PyPDF2
                        pdf_reader = PyPDF2.PdfReader(uploaded_file)
                        st.session_state.reference_text = "".join([page.extract_text() + "\n" for page in pdf_reader.pages])
                    elif uploaded_file.name.endswith('.docx'):
                        import docx
                        doc = docx.Document(uploaded_file)
                        st.session_state.reference_text = "".join([para.text + "\n" for para in doc.paragraphs])
                    elif uploaded_file.name.endswith('.txt'):
                        st.session_state.reference_text = uploaded_file.read().decode("utf-8")
                        
                    if st.session_state.reference_text and st.session_state.reference_text.strip():
                        st.success("✅ Text extracted successfully! The AI will strictly use this as context.")
                    else:
                        st.warning("⚠️ The file appears to be empty or unreadable.")
                        st.session_state.reference_text = None
                except Exception as e:
                    st.error(f"Error reading file: {e}")
                    st.session_state.reference_text = None
        else:
            st.session_state.reference_text = None

        st.write("")
        # Determine if user is allowed to proceed
        can_proceed = bool(st.session_state.selected_domains) or bool(st.session_state.get('reference_text'))
        
        if can_proceed:
            if st.session_state.selected_domains:
                try:
                    from ui_pages import get_domain_color
                except Exception:
                    get_domain_color = lambda d: "#3b82f6"
                    
                chips = "".join([f"<span style='display:inline-block; padding:4px 12px; margin:3px; border-radius:20px; font-size:0.8rem; font-weight:600; background:rgba(255,255,255,0.08); border:1px solid {get_domain_color(d)}; color:{get_domain_color(d)} !important;'>{d}</span>" for d in st.session_state.selected_domains])
                st.markdown(f"**Domains Locked:** <br>{chips}", unsafe_allow_html=True)
            
            if st.button("Next: Configure Test Options ➡️", type="primary"):
                # If they only uploaded a file, we assign a dummy domain to prevent math crashes in ai_engine
                if not st.session_state.selected_domains:
                    st.session_state.selected_domains = ["Custom Reference Document"]
                st.session_state.dashboard_step = 'configure_test'
                st.rerun()
        else:
            st.info("Select at least one domain OR upload a document to proceed.")

    # --- STEP 2: CONFIGURE TEST ---
    elif st.session_state.dashboard_step == 'configure_test':
        st.button("⬅️ Back to Domains/Upload", on_click=lambda: st.session_state.update(dashboard_step='select_domain'))

        st.markdown("<h2>Configure Your Test ⚙️</h2>", unsafe_allow_html=True)
        st.write(f"**Selected Subjects:** {', '.join(st.session_state.selected_domains)}")
        st.divider()

        st.info("""
        **📋 Test Instructions & Grading System:**
        *   **Base Points:** Correct Answer = +10 Points.
        *   **Difficulty Multiplier:** Easy (x1), Medium (x1.5), Hard (x2.0), Mixed (x1.5).
        *   **Speed Bonus:** +5 Points for answering within 20 seconds.
        *   **Auto-Submit:** If the timer reaches 0, the test will automatically advance or conclude.
        *   **Sections:** Questions will be distributed equally among your selected domains and presented in order.
        """)

        cfg1, cfg2, cfg3 = st.columns(3)
        with cfg1:
            difficulty = st.select_slider("Difficulty Level", options=["Easy", "Medium", "Hard", "Mixed"], value="Medium")
            multiplier_map = {"Easy": 1.0, "Medium": 1.5, "Hard": 2.0, "Mixed": 1.5}

        with cfg2:
            timer_choice = st.selectbox("Time per Question", ["30 Seconds", "1 Minute", "2 Minutes", "5 Minutes", "No Timer"])
            timer_map = {"30 Seconds": 30, "1 Minute": 60, "2 Minutes": 120, "5 Minutes": 300, "No Timer": 0}

        with cfg3:
            num_questions = st.number_input("Total Number of Questions", min_value=1, max_value=50, value=15)

        st.write("<br>", unsafe_allow_html=True)
        if st.button("🚀 START EXAM SIMULATION", type="primary", use_container_width=True):
            st.session_state.test_config = {
                "difficulty": difficulty,
                "multiplier": multiplier_map[difficulty],
                "timer_seconds": timer_map[timer_choice],
                "num_questions": num_questions,
                "reference_text": st.session_state.get('reference_text', None)  # Retrieve text from session
            }
            st.session_state.quiz_data = None
            st.session_state.current_q_index = 0
            st.session_state.user_answers = []
            st.session_state.total_score = 0
            st.session_state.clear_counter = 0
            st.session_state.test_saved = False
            st.session_state.dashboard_step = 'test_execution'
            st.rerun()

    # --- STEP 3: TEST EXECUTION ---
    elif st.session_state.dashboard_step == 'test_execution':
        st.markdown("<h2 style='text-align: center; color: #ef4444 !important;'>🔴 Live Exam Environment</h2>", unsafe_allow_html=True)

        if st.session_state.quiz_data is None:
            with st.spinner("⚡ Fetching initial questions to start your test immediately..."):
                try:
                    import ai_engine
                    diff_instruction = st.session_state.test_config['difficulty']
                    if diff_instruction == "Mixed": diff_instruction = "Mixed (Equal distribution of Easy, Medium, and Hard)"

                    total_req = st.session_state.test_config['num_questions']
                    first_chunk = min(5, total_req) 
                    
                    ref_text = st.session_state.test_config.get('reference_text', None)

                    # 1. Main thread fetch
                    st.session_state.quiz_data = ai_engine.generate_test_questions(
                        st.session_state.selected_domains, first_chunk, diff_instruction, reference_text=ref_text
                    )
                    st.session_state.q_start_time = time.time()

                    # 2. Background thread fetch
                    remaining_q = total_req - first_chunk
                    if remaining_q > 0:
                        def fetch_rest_questions():
                            try:
                                rest_data = ai_engine.generate_test_questions(
                                    st.session_state.selected_domains, remaining_q, diff_instruction, reference_text=ref_text
                                )
                                st.session_state.quiz_data.extend(rest_data)
                            except Exception as e:
                                print(f"Background fetch error: {e}")

                        bg_thread = threading.Thread(target=fetch_rest_questions)
                        add_script_run_ctx(bg_thread) 
                        bg_thread.start()

                    st.rerun()
                except Exception as e:
                    st.error(f"API Error: {e}")
                    if st.button("Try Again"): st.rerun()
                    return

        # 🎯 SAFEGUARD LOGIC
        total_intended = st.session_state.test_config['num_questions']
        total_loaded = len(st.session_state.quiz_data)
        current_idx = st.session_state.current_q_index

        if current_idx < total_loaded:
            q_data = st.session_state.quiz_data[current_idx]

            if st.session_state.test_config['timer_seconds'] > 0:
                elapsed = int(time.time() - st.session_state.q_start_time)
                remaining = max(0, st.session_state.test_config['timer_seconds'] - elapsed)

                js_timer = f"""
                <div id="countdown_display_{current_idx}" style="font-size: 1.5rem; color: #ef4444; font-weight: bold; text-align: right; font-family: sans-serif;">⏱️ Time Left: --:--</div>
                <script>
                    var timeLeft = {remaining};
                    var display = document.getElementById('countdown_display_{current_idx}');
                    var timerId = setInterval(function() {{
                        if (timeLeft <= 0) {{
                            clearInterval(timerId); display.innerHTML = "⏱️ Time's Up!";
                            var buttons = window.parent.document.querySelectorAll('button');
                            for (var i = 0; i < buttons.length; i++) {{
                                var btnText = buttons[i].innerText || buttons[i].textContent;
                                if (btnText.includes("Submit Answer") || btnText.includes("Submit & End Test")) {{ buttons[i].click(); break; }}
                            }}
                        }} else {{
                            var m = Math.floor(timeLeft / 60); var s = timeLeft % 60;
                            display.innerHTML = "⏱️ Time Left: " + m + ":" + (s < 10 ? "0" : "") + s;
                            timeLeft--;
                        }}
                    }}, 1000);
                </script>
                """
                components.html(js_timer, height=40)

            st.progress((current_idx) / total_intended)
            current_domain_tag = q_data.get('domain', 'General')
            
            try:
                from ui_pages import get_domain_color
                domain_color = get_domain_color(current_domain_tag)
            except Exception:
                domain_color = "#3b82f6"
                
            st.write(f"**Question {current_idx + 1} of {total_intended}** | Section: **{current_domain_tag}** | Difficulty: {st.session_state.test_config['difficulty']}")

            st.markdown(f"<div class='question-box' style='border-left: 4px solid {domain_color} !important; text-align:left;'><h3>{q_data['question']}</h3></div>", unsafe_allow_html=True)

            form_key = f"q_form_{current_idx}_{st.session_state.clear_counter}"
            options_with_skip = q_data['options'] + ["⏭️ Leave Blank / Skip"]

            with st.form(key=form_key):
                radio_key = f"radio_q_{current_idx}_{st.session_state.clear_counter}"
                user_choice = st.radio("Select your answer:", options_with_skip, index=None, key=radio_key)

                col_sub, col_leave = st.columns([4, 1])
                with col_sub:
                    btn_label = "Submit Answer & Next ➡️" if current_idx < total_intended - 1 else "Submit & End Test 🏁"
                    submitted = st.form_submit_button(btn_label, type="primary")
                with col_leave:
                    force_end = st.form_submit_button("Force End Test 🚪")

                if force_end:
                    st.session_state.dashboard_step = 'test_results'
                    st.rerun()
                elif submitted:
                    time_taken = time.time() - st.session_state.q_start_time
                    points_earned = 0

                    if user_choice is None or user_choice == "⏭️ Leave Blank / Skip":
                        is_correct, status = False, "Skipped"
                        final_choice = "Skipped (Left Blank)"
                    else:
                        is_correct = (user_choice == q_data['answer'])
                        status = "Correct" if is_correct else "Incorrect"
                        final_choice = user_choice

                    if is_correct:
                        points_earned = 10 * st.session_state.test_config['multiplier']
                        if time_taken < 20.0 and st.session_state.test_config['timer_seconds'] > 0:
                            points_earned += 5

                    st.session_state.total_score += points_earned
                    st.session_state.user_answers.append({
                        "domain": current_domain_tag, "question": q_data['question'],
                        "your_answer": final_choice,
                        "correct_answer": q_data['answer'], "status": status,
                        "explanation": q_data['explanation'], "points": points_earned
                    })
                    st.session_state.current_q_index += 1
                    st.session_state.q_start_time = time.time()
                    if st.session_state.current_q_index >= total_intended: st.session_state.dashboard_step = 'test_results'
                    st.rerun()

    # --- STEP 4: TEST RESULTS ---
    elif st.session_state.dashboard_step == 'test_results':
        is_challenge_test = bool(st.session_state.get('current_room_code'))
        room_code = st.session_state.get('current_room_code')

        st.markdown("<h1 style='text-align: center; color: #10b981 !important;'>🎉 Test Completed!</h1>", unsafe_allow_html=True)

        total_attempted = len([a for a in st.session_state.user_answers if a['status'] != "Skipped"])
        skipped_count = len([a for a in st.session_state.user_answers if a['status'] == "Skipped"])
        correct_count = sum(1 for a in st.session_state.user_answers if a['status'] == "Correct")
        incorrect_count = total_attempted - correct_count
        accuracy = int((correct_count / max(total_attempted, 1)) * 100) if total_attempted > 0 else 0

        if not st.session_state.get('test_saved', False):
            import database
            total_questions_configured = st.session_state.test_config.get('num_questions', len(st.session_state.user_answers))
            database.save_test_history(
                st.session_state.username,
                st.session_state.selected_domains,
                total_attempted,
                total_questions_configured,
                st.session_state.total_score,
                accuracy
            )
            database.update_user_stats(st.session_state.username, st.session_state.total_score)
            st.session_state.test_saved = True

        if is_challenge_test and not st.session_state.get('room_result_submitted', False):
            import database
            time_taken = time.time() - st.session_state.get('challenge_test_start_time', time.time())
            database.submit_room_result(room_code, st.session_state.username, st.session_state.total_score, time_taken)
            st.session_state.room_result_submitted = True

        if accuracy >= 80 and total_attempted > 0: st.success("🌟 **Outstanding Performance!** You are absolutely ready to ace this technical round. Your concepts are rock solid. Keep up the brilliant work!")
        elif accuracy >= 50 and total_attempted > 0: st.info("👍 **Great Effort!** You have a very solid foundation. Review the skipped and incorrect questions below, and you'll be unstoppable in the actual interview.")
        else: st.warning("💪 **Good Try!** Every expert was once a beginner. Use the detailed AI explanations below to learn these concepts, and you will see massive improvements next time. Keep pushing!")
        st.divider()

        r1, r2, r3, r4, r5 = st.columns(5)
        with r1: st.markdown(f"<div class='analytics-box'><h4>Score</h4><h2>{st.session_state.total_score}</h2></div>", unsafe_allow_html=True)
        with r2: st.markdown(f"<div class='analytics-box'><h4>Accuracy</h4><h2>{accuracy}%</h2></div>", unsafe_allow_html=True)
        with r3: st.markdown(f"<div class='analytics-box'><h4>Correct</h4><h2 style='color: #10b981;'>{correct_count}</h2></div>", unsafe_allow_html=True)
        with r4: st.markdown(f"<div class='analytics-box'><h4>Incorrect</h4><h2 style='color: #ef4444;'>{incorrect_count}</h2></div>", unsafe_allow_html=True)
        with r5: st.markdown(f"<div class='analytics-box'><h4>Skipped</h4><h2 style='color: #f59e0b;'>{skipped_count}</h2></div>", unsafe_allow_html=True)

        if is_challenge_test:
            st.divider()
            import database
            show_lb = database.get_room_show_leaderboard(room_code)
            if show_lb:
                st.markdown("<p style='font-weight:700; font-size:1.15rem; margin-bottom:10px;'>🏆 Live Room Leaderboard</p>", unsafe_allow_html=True)
                try:
                    from streamlit_autorefresh import st_autorefresh
                    st_autorefresh(interval=4000, key="results_leaderboard_refresh")
                except Exception:
                    pass
                board = database.get_live_leaderboard(room_code)
                medals = {1: "🥇", 2: "🥈", 3: "🥉"}
                for rank, (b_username, b_score, b_time) in enumerate(board, start=1):
                    is_me = (b_username == st.session_state.username)
                    highlight = "border: 1px solid #3b82f6; background: rgba(59,130,246,0.10);" if is_me else ""
                    badge = medals.get(rank, f"#{rank}")
                    st.markdown(f"""
                    <div class='participant-chip' style='{highlight}'>
                        <div class='chip-avatar'>{badge}</div>
                        <b>{b_username}{" (You)" if is_me else ""}</b>
                        <span class='chip-status'>{b_score:.0f} pts</span>
                    </div>
                    """, unsafe_allow_html=True)
                st.caption("This updates live every few seconds as other participants finish.")
            else:
                st.info("The host has kept individual scores private for this room — only your own result above is visible to you.")

        st.divider()
        st.subheader("Detailed Section-Wise Analysis")
        if is_challenge_test:
            st.caption("Live-challenge mode keeps this to right/wrong + the correct answer — full AI explanations are for solo mock assessments.")

        for i, ans_data in enumerate(st.session_state.user_answers):
            domain_label = ans_data.get('domain', 'General')
            with st.expander(f"Q{i+1} [{domain_label}]: {ans_data['question']}"):
                if ans_data['status'] == "Correct": st.success(f"✅ Your Answer: {ans_data['your_answer']} (+{ans_data['points']} pts)")
                elif ans_data['status'] == "Skipped":
                    st.warning(f"⏭️ Skipped / Time Out (0 pts)")
                    st.success(f"🎯 Correct Answer: {ans_data['correct_answer']}")
                else:
                    st.error(f"❌ Your Answer: {ans_data['your_answer']} (0 pts)")
                    st.success(f"🎯 Correct Answer: {ans_data['correct_answer']}")

                if not is_challenge_test:
                    st.info(f"**Explanation:** {ans_data['explanation']}")

                if st.button("🔖 Save to Bookmarks", key=f"save_{i}"):
                    import database
                    conn = database.get_connection()
                    c = conn.cursor()
                    c.execute("INSERT INTO saved_questions (username, category, question, options, answer, explanation, user_notes) VALUES (?, ?, ?, ?, ?, ?, ?)",
                              (st.session_state.username, domain_label, ans_data['question'], "Saved Options", ans_data['correct_answer'], ans_data['explanation'], ""))
                    conn.commit()
                    conn.close()
                    st.toast("Question saved to your bookmarks!")

        st.write("<br>", unsafe_allow_html=True)
        if st.button("Return to Dashboard 🏠", type="primary", use_container_width=True):
            st.session_state.dashboard_step = 'select_domain'
            st.session_state.selected_domains = []
            st.session_state.reference_text = None # Clear file session on exit
            st.session_state.current_room_code = None
            st.session_state.challenge_view = 'menu'
            st.session_state.room_result_submitted = False
            st.rerun()

# ------------------------------------------------------------------
# PROFILE PAGE
# ------------------------------------------------------------------

def page_profile():
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT email, password, profile_pic FROM users WHERE username = ?", (st.session_state.username,))
    user_data = c.fetchone()
    current_email = user_data[0]
    current_password = user_data[1]
    current_pic = user_data[2]
    conn.close()

    st.markdown("<div style='display:flex; align-items:center; gap:10px;'><div class='profile-header'>User Profile</div><span style='font-size:2.4rem;'>✨</span></div>", unsafe_allow_html=True)

    col_img, col_info = st.columns([1, 4])
    with col_img:
        if current_pic and len(current_pic) > 10:
            st.markdown(f'<img src="data:image/png;base64,{current_pic}" width="100" style="border-radius: 50%;">', unsafe_allow_html=True)
        else:
            st.markdown(f"<h1 style='font-size: 5rem; margin: 0;'>{current_pic}</h1>", unsafe_allow_html=True)

    with col_info:
        st.write(f"### {st.session_state.username}")
        st.write(f"📧 {current_email}")

    st.divider()

    # --- XP & RANK with progress bar ---
    total_points, tests_completed = database.get_user_stats(st.session_state.username)

    if total_points < 1000: rank = "Beginner 🥉"
    elif total_points < 5000: rank = "Intermediate 🥈"
    elif total_points < 15000: rank = "Advanced 🥇"
    else: rank = "Pro Hacker 💎"

    st.subheader("Your Progress & Rank")
    r1, r2, r3 = st.columns(3)
    with r1: st.metric(label="Total XP", value=f"{total_points:,}")
    with r2: st.metric(label="Current Rank", value=rank)
    with r3: st.metric(label="Tests Completed", value=tests_completed)

    render_xp_bar(total_points, rank)

    st.divider()

    st.write("---")
    # 🎯 NEW PRO AVATAR SELECTION
    st.markdown("### Customize Avatar 🖼️")
    st.write("Choose a premium 3D avatar for your profile:")
    
    presets = get_avatar_presets(st.session_state.username)
    avatar_names = list(presets.keys())
    
    col_sel, col_prev = st.columns([2, 1])
    
    with col_sel:
        selected_name = st.selectbox("Select Avatar", avatar_names)
        selected_url = presets[selected_name]
        
        if st.button("Update Avatar", use_container_width=True):
            # Save the new URL directly to the database
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("UPDATE users SET profile_pic = ? WHERE username = ?", (selected_url, st.session_state.username))
            conn.commit()
            conn.close()
            
            st.success("Avatar updated successfully! ⚡")
            time.sleep(1)
            st.rerun()
            
    with col_prev:
        st.markdown("**Preview:**")
        # Shows a live preview of the selected avatar before updating
        st.markdown(f'<div style="display:flex; justify-content:center;"><img src="{selected_url}" width="100" style="border-radius: 50%; border: 2px solid #3b82f6; background: rgba(255,255,255,0.05);"></div>', unsafe_allow_html=True)

    uploaded_file = st.file_uploader("OR Upload Custom Photo (PNG/JPG, Max 2MB)", type=['png', 'jpg', 'jpeg'])

    if st.button("🖼️ Update Profile Picture"):
        conn = database.get_connection()
        c = conn.cursor()
        if uploaded_file is not None:
            b64_string = get_image_base64(uploaded_file)
            c.execute("UPDATE users SET profile_pic = ? WHERE username = ?", (b64_string, st.session_state.username))
            st.success("Custom photo updated!")
        else:
            c.execute("UPDATE users SET profile_pic = ? WHERE username = ?", (selected_url, st.session_state.username))
            st.success("Avatar updated!")
        conn.commit()
        conn.close()
        time.sleep(1)
        st.rerun()

    st.divider()

    st.subheader("Security Settings 🔐")
    old_pass = st.text_input("🔒 Current Password", type="password")
    new_pass = st.text_input("🔑 New Password", type="password")
    confirm_new_pass = st.text_input("🔑 Confirm New Password", type="password")

    if st.button("🔐 Update Password"):
        if not old_pass or not new_pass or not confirm_new_pass: st.warning("Please fill all password fields.")
        elif old_pass != current_password: st.error("Incorrect current password!")
        elif new_pass != confirm_new_pass: st.error("New passwords do not match!")
        else:
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("UPDATE users SET password = ? WHERE username = ?", (new_pass, st.session_state.username))
            conn.commit()
            conn.close()
            st.success("Password updated successfully!")

# ------------------------------------------------------------------
# CHALLENGE / MULTIPLAYER LOBBY
# ------------------------------------------------------------------

def page_challenge():
    try:
        render_room_chat_sidebar()
    except Exception:
        pass 

    import json
    import time
    try:
        from streamlit_autorefresh import st_autorefresh
    except ImportError:
        st.error("⚠️ Library Missing! Terminal mein jao aur yeh command type karo: pip install streamlit-autorefresh")
        st.stop()

    st.markdown("<div style='display:flex; align-items:center; justify-content:flex-start; gap:12px;'><span style='font-size:2.4rem;'>⚔️</span><div class='profile-header' style='font-size: 3rem;'>Peer Challenge Lobby</div></div>", unsafe_allow_html=True)
    st.write("Host a synchronized tech sprint or join an existing room with a code.")

    if 'challenge_view' not in st.session_state: st.session_state.challenge_view = 'menu'
    if 'current_room_code' not in st.session_state: st.session_state.current_room_code = None
    if 'generating_test' not in st.session_state: st.session_state.generating_test = False
    if 'challenge_uploaded_file' not in st.session_state: st.session_state.challenge_uploaded_file = None

    def render_participant_list(participants, host_username, allow_actions=False, room_code=None):
        for p in participants:
            p_username, p_status = p
            is_host = (p_username == host_username)
            avatar_class = "chip-host" if is_host else "chip-avatar"
            avatar_icon = "👑" if is_host else "👤"
            status_text = "Host" if is_host else p_status.capitalize()
            st.markdown(f"<div class='participant-chip'><div class='{avatar_class} chip-avatar'>{avatar_icon}</div><b>{p_username}</b><span class='chip-status'>{status_text}</span></div>", unsafe_allow_html=True)
            if allow_actions and not is_host and p_status == 'pending':
                col_app, col_rej = st.columns(2)
                with col_app:
                    if st.button("✅ Approve", key=f"app_{p_username}"):
                        import database
                        database.update_participant_status(room_code, p_username, 'approved')
                        st.rerun()
                with col_rej:
                    if st.button("❌ Reject", key=f"rej_{p_username}"):
                        import database
                        database.update_participant_status(room_code, p_username, 'rejected')
                        st.rerun()

    if st.session_state.challenge_view == 'menu':
        tab1, tab2 = st.tabs(["🚀 Join a Test", "👑 Host a Test"])

        with tab1:
            st.subheader("Join via Room Code")
            room_code_input = st.text_input("Enter 6-Digit Room Code:", max_chars=6).upper()
            if st.button("Join Room", type="primary"):
                if len(room_code_input) == 6:
                    import database
                    result = database.join_challenge_room(room_code_input, st.session_state.username)
                    if result == "invalid": st.error("Invalid or expired room code.")
                    elif result == "full": st.error("Room is currently full.")
                    else:
                        st.session_state.current_room_code = room_code_input
                        st.session_state.challenge_view = 'guest_lobby'
                        st.rerun()
                else:
                    st.warning("Please enter a valid 6-digit code.")

        with tab2:
            st.subheader("Create & Configure Test Room")
            col1, col2 = st.columns(2)
            with col1:
                is_private = st.toggle("🔒 Private Room (Requires Host Approval)", value=False)
                show_leaderboard = st.toggle("📊 Show Public Leaderboard after test", value=True)
            with col2:
                max_participants = st.number_input("Max Participants Limit", min_value=2, max_value=50, value=10)

            st.info("Test topics and difficulty will be configured inside the lobby!")
            if st.button("Create Room & Enter Lobby", type="primary"):
                import database
                new_code = database.create_challenge_room(st.session_state.username, is_private, max_participants, show_leaderboard)
                st.session_state.current_room_code = new_code
                st.session_state.generating_test = False
                st.session_state.challenge_view = 'host_lobby'
                st.rerun()

    elif st.session_state.challenge_view == 'host_lobby':

        if st.session_state.generating_test:
            count = st_autorefresh(interval=100, limit=2, key="ai_trigger")
            st.markdown("<h2 style='text-align:center;'>🚀 Launching Multiplayer Test...</h2>", unsafe_allow_html=True)
            
            if count > 0:
                with st.spinner("AI is analyzing reference material & crafting unique questions... Please wait (10-20s)"):
                    try:
                        import database
                        import ai_engine
                        
                        params = st.session_state.test_setup_params
                        domain_list = params['domains']
                        diff_instr = "Mixed" if params['diff'] == "Mixed" else params['diff']

                        # Pass the uploaded file to the AI engine
                        quiz_data = ai_engine.generate_test_questions(
                            domain_list, 
                            params['num_q'], 
                            diff_instr,
                            uploaded_file=st.session_state.challenge_uploaded_file
                        )

                        database.start_room_test(st.session_state.current_room_code, json.dumps(quiz_data))

                        st.session_state.quiz_data = quiz_data
                        st.session_state.q_start_time = time.time()
                        st.session_state.challenge_test_start_time = time.time()
                        st.session_state.room_result_submitted = False
                        st.session_state.test_config = {"difficulty": params['diff'], "multiplier": 1.5, "timer_seconds": 60, "num_questions": params['num_q']}
                        st.session_state.current_q_index = 0
                        st.session_state.user_answers = []
                        st.session_state.total_score = 0
                        st.session_state.clear_counter = 0
                        st.session_state.test_saved = False
                        
                        st.session_state.dashboard_step = 'test_execution'
                        st.session_state.page = 'dashboard'
                        st.session_state.generating_test = False
                        st.session_state.challenge_uploaded_file = None # Clear file after generation
                        st.rerun()
                    except Exception as e:
                        st.session_state.generating_test = False
                        st.error(f"Error generating test: {e}")
                        if st.button("Try Again"): st.rerun()
            else:
                with st.spinner("Synchronizing room and securing AI connection..."):
                    pass

        else:
            st_autorefresh(interval=3000, key="host_live_refresh")
            st.markdown(f"<div style='text-align:center; margin-bottom: 20px;'><p style='color:#94a3b8 !important; margin-bottom: 6px;'>🎉 Room Created — Share this code</p><span class='room-code-badge'>{st.session_state.current_room_code}</span></div>", unsafe_allow_html=True)

            import database
            room_details = database.get_room_details(st.session_state.current_room_code)
            host_username = room_details[0] if room_details else ""

            c1, c2 = st.columns([2, 2])
            with c1:
                st.subheader("👥 Participants in Lobby")
                participants = database.get_room_participants(st.session_state.current_room_code)

                if not participants: st.write("No one has joined yet...")
                else:
                    render_participant_list(participants, host_username, allow_actions=True, room_code=st.session_state.current_room_code)

            with c2:
                st.subheader("⚙️ Configure Room Test")

                predefined_domains = [
                    "Core CS Fundamentals", "English Grammar", "Quantitative Aptitude",
                    "Logical Reasoning", "Database Management Systems (DBMS)",
                    "Computer Networks", "Operating Systems", "Cloud Computing"
                ]
                all_options = predefined_domains + [t for t in st.session_state.challenge_custom_topics if t not in predefined_domains]

                room_domains = st.multiselect(
                    "Select one or more topics for this room:",
                    options=all_options,
                    default=[d for d in st.session_state.challenge_selected_domains if d in all_options],
                    key="challenge_domain_multiselect"
                )

                cust_col, add_col = st.columns([3, 1])
                with cust_col:
                    custom_topic_input = st.text_input("Add a custom topic:", key="challenge_custom_topic_input", placeholder="e.g., System Design, ReactJS")
                with add_col:
                    st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
                    if st.button("➕ Add", key="challenge_add_custom_btn", use_container_width=True) and custom_topic_input:
                        for t in [x.strip() for x in custom_topic_input.split(",") if x.strip()]:
                            if t not in st.session_state.challenge_custom_topics and t not in predefined_domains:
                                st.session_state.challenge_custom_topics.append(t)
                            if t not in room_domains:
                                room_domains.append(t)
                        st.session_state.challenge_selected_domains = room_domains
                        st.rerun()

                st.session_state.challenge_selected_domains = room_domains

                if room_domains:
                    try:
                        from ui_pages import get_domain_color
                    except Exception:
                        get_domain_color = lambda d: "#3b82f6" 
                    chips = "".join([f"<span style='display:inline-block; padding:3px 10px; margin:2px; border-radius:16px; font-size:0.75rem; font-weight:600; background:rgba(255,255,255,0.08); border:1px solid {get_domain_color(d)}; color:{get_domain_color(d)} !important;'>{d}</span>" for d in room_domains])
                    st.markdown(f"<div style='margin: 6px 0 12px 0;'>{chips}</div>", unsafe_allow_html=True)

                col_diff, col_num = st.columns(2)
                with col_diff:
                    difficulty = st.selectbox("Difficulty:", ["Easy", "Medium", "Hard", "Mixed"], index=1)
                with col_num:
                    num_q = st.number_input("Number of Questions:", min_value=1, max_value=25, value=5)

                # 🎯 NEW: RAG FILE UPLOADER
                st.markdown("<br>", unsafe_allow_html=True)
                with st.expander("📎 Generate from Document (PDF/Word/Image)"):
                    uploaded_file = st.file_uploader("Upload reference material. AI will form questions based on this document.", type=["pdf", "docx", "png", "jpg", "jpeg"], key="challenge_uploader")
                    st.session_state.challenge_uploaded_file = uploaded_file

                st.warning("Once you click Start, the AI will generate the test and pull all approved participants into the live exam.")

                if st.button("🚀 Start Test For All", type="primary", use_container_width=True):
                    if not room_domains:
                        st.error("Select at least one topic before starting.")
                    else:
                        st.session_state.test_setup_params = {
                            "domains": room_domains,
                            "diff": difficulty,
                            "num_q": num_q
                        }
                        st.session_state.generating_test = True
                        st.rerun()

                if st.button("🛑 Close Room", type="secondary"):
                    import database
                    database.close_challenge_room(st.session_state.current_room_code)
                    st.session_state.challenge_view = 'menu'
                    st.session_state.current_room_code = None
                    st.rerun()

    elif st.session_state.challenge_view == 'guest_lobby':
        st_autorefresh(interval=3000, key="guest_live_refresh")
        st.markdown(f"<div style='text-align:center; margin-bottom: 20px;'><p style='color:#94a3b8 !important; margin-bottom: 6px;'>🚪 Waiting Room</p><span class='room-code-badge'>{st.session_state.current_room_code}</span></div>", unsafe_allow_html=True)

        import database
        room_details = database.get_room_details(st.session_state.current_room_code)
        if not room_details:
            st.error("🚪 The host has closed this room — you've been moved out automatically.")
            if st.button("Go Back"):
                st.session_state.challenge_view = 'menu'
                st.session_state.current_room_code = None
                st.rerun()
            return

        host_username, room_status, quiz_data_str = room_details
        participants = database.get_room_participants(st.session_state.current_room_code)
        my_status = 'unknown'
        for p in participants:
            if p[0] == st.session_state.username: my_status = p[1]

        st.markdown("#### 👥 Participants:")
        render_participant_list(participants, host_username)
        st.divider()

        if my_status == 'pending':
            st.warning("⏳ Waiting for the Host to approve your entry...")
        elif my_status == 'rejected':
            st.error("❌ The host declined your entry to this room.")
        elif my_status == 'approved':
            if room_status == 'active':
                st.success("🚀 Test has started! Redirecting...")
                st.session_state.quiz_data = json.loads(quiz_data_str)
                st.session_state.q_start_time = time.time()
                st.session_state.challenge_test_start_time = time.time()
                st.session_state.room_result_submitted = False
                st.session_state.test_config = {"difficulty": "Host Default", "multiplier": 1.5, "timer_seconds": 60, "num_questions": len(st.session_state.quiz_data)}
                st.session_state.current_q_index = 0
                st.session_state.user_answers = []
                st.session_state.total_score = 0
                st.session_state.clear_counter = 0
                st.session_state.test_saved = False
                st.session_state.dashboard_step = 'test_execution'
                st.session_state.page = 'dashboard'
                st.rerun()
            else:
                st.success("✅ You are in! Waiting for the host to configure and start the synchronized test...")

        if st.button("Leave Room", type="secondary"):
            st.session_state.challenge_view = 'menu'
            st.session_state.current_room_code = None
            st.rerun()

# ------------------------------------------------------------------
# SAVED QUESTIONS
# ------------------------------------------------------------------

def page_saved_questions():
    conn = database.get_connection()
    c = conn.cursor()
    c.execute("SELECT id, category, question, answer, explanation, user_notes FROM saved_questions WHERE username = ? ORDER BY id DESC", (st.session_state.username,))
    saved_data = c.fetchall()
    conn.close()

    if not saved_data:
        st.info("You haven't saved any questions yet. While reviewing your results after a test, hit **🔖 Save to Bookmarks** on anything you want to revisit.")
        return

    categories = list(dict.fromkeys([row[1] for row in saved_data]))
    f1, f2 = st.columns([2, 2])
    with f1:
        selected_cat = st.selectbox("Filter by topic", ["All Topics"] + categories, key="vault_cat_filter")
    with f2:
        search_term = st.text_input("Search within your bookmarks", placeholder="Type a keyword…", key="vault_search")

    st.markdown(f"<p style='color:#94a3b8; margin: 6px 0 16px 0; font-size:0.88rem;'>{len(saved_data)} question(s) bookmarked</p>", unsafe_allow_html=True)

    for row in saved_data:
        q_id, cat, q_text, ans, exp, notes = row
        if selected_cat != "All Topics" and selected_cat != cat:
            continue
        if search_term and search_term.lower() not in q_text.lower() and search_term.lower() not in (notes or "").lower():
            continue

        accent = get_domain_color(cat)
        with st.container(border=True):
            st.markdown(f"""
            <div style="border-left: 3px solid {accent}; padding-left: 14px;">
                <span style="display:inline-block; padding:2px 10px; border-radius:12px; font-size:0.72rem; font-weight:700;
                             background:rgba(255,255,255,0.06); border:1px solid {accent}; color:{accent} !important; margin-bottom:8px;">{cat}</span>
                <p style="font-size:1rem; margin: 6px 0 2px 0;">{q_text}</p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander("View answer & your notes"):
                st.success(f"**Correct Answer:** {ans}")
                if exp and exp != "Saved Options":
                    st.info(f"**Explanation:** {exp}")

                new_notes = st.text_area("Your logic / notes on this question:", value=notes if notes else "", key=f"note_{q_id}", placeholder="Write how you'd reason through this next time…")
                nb1, nb2 = st.columns([1, 1])
                with nb1:
                    if st.button("💾 Save Note", key=f"btn_{q_id}", use_container_width=True):
                        conn = database.get_connection()
                        conn.cursor().execute("UPDATE saved_questions SET user_notes = ? WHERE id = ?", (new_notes, q_id))
                        conn.commit()
                        conn.close()
                        st.toast("Notes saved.")
                with nb2:
                    if st.button("🗑️ Remove Bookmark", key=f"del_{q_id}", use_container_width=True):
                        database.delete_saved_question(q_id, st.session_state.username)
                        st.toast("Bookmark removed.")
                        st.rerun()

# ------------------------------------------------------------------
# HISTORY PAGE
# ------------------------------------------------------------------

def page_history():
    st.markdown("<div style='display:flex; align-items:center; gap:12px;'><div class='profile-header' style='font-size: 3rem;'>Test History</div><span style='font-size:2.4rem;'>📜</span></div>", unsafe_allow_html=True)
    st.write("Review your past performance and track your accuracy over time.")

    history_data = database.get_user_history(st.session_state.username)

    if not history_data:
        st.info("You haven't completed any tests yet. Head over to the Dashboard to start your first simulation!")
    else:
        # Header row (plain columns, no stray wrapping div)
        h1, h2, h3, h4, h5 = st.columns([2, 3, 1, 1, 1.5])
        with h1: st.markdown("**Date**")
        with h2: st.markdown("**Topic(s)**")
        with h3: st.markdown("**Score**")
        with h4: st.markdown("**Accuracy**")
        with h5: st.markdown("**Attempted**")
        st.divider()

        # Each row rendered in its own bordered container -> clean "card row" look,
        # and no manual HTML div juggling that can misalign.
        for row in history_data:
            date, domains, attempted, total, score, accuracy = row

            if attempted is None or (attempted == 0 and total > 0): attempted = total
            # Guard against an empty domains string: "**" + "" + "**" == "****",
            # which Markdown reads as a horizontal rule, not bold text.
            domains_display = domains.strip() if domains and domains.strip() else "—"

            with st.container(border=True):
                c1, c2, c3, c4, c5 = st.columns([2, 3, 1, 1, 1.5])
                with c1: st.markdown(f"<span style='color: #cbd5e1; font-size: 0.9rem;'>{date}</span>", unsafe_allow_html=True)
                with c2: st.markdown(f"**{domains_display}**")
                with c3: st.markdown(f"<span style='color: #3b82f6; font-weight: bold;'>{score} pts</span>", unsafe_allow_html=True)

                acc_color = "#10b981" if accuracy >= 70 else ("#f59e0b" if accuracy >= 40 else "#ef4444")
                with c4: st.markdown(f"<span style='color: {acc_color}; font-weight: bold;'>{accuracy}%</span>", unsafe_allow_html=True)

                with c5: st.markdown(f"**{attempted} / {total}**")