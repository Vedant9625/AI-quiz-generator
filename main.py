import streamlit as st
import database
import ui_pages

st.set_page_config(page_title="Interview Simulator", page_icon="🎓", layout="wide", initial_sidebar_state="auto")
database.init_db()

# Setup Global Session States
if 'page' not in st.session_state: st.session_state.page = 'landing'
if 'username' not in st.session_state: st.session_state.username = None
if 'auth_mode' not in st.session_state: st.session_state.auth_mode = 'Login'
if 'login_failed' not in st.session_state: st.session_state.login_failed = False
if 'signup_step' not in st.session_state: st.session_state.signup_step = 'details'
if 'generated_otp' not in st.session_state: st.session_state.generated_otp = None
if 'temp_signup_data' not in st.session_state: st.session_state.temp_signup_data = {}

if 'dashboard_step' not in st.session_state: st.session_state.dashboard_step = 'select_domain'
if 'selected_domains' not in st.session_state: st.session_state.selected_domains = []
if 'custom_topics' not in st.session_state: st.session_state.custom_topics = [] 
if 'quiz_data' not in st.session_state: st.session_state.quiz_data = None
if 'current_q_index' not in st.session_state: st.session_state.current_q_index = 0
if 'user_answers' not in st.session_state: st.session_state.user_answers = []
if 'total_score' not in st.session_state: st.session_state.total_score = 0
if 'q_start_time' not in st.session_state: st.session_state.q_start_time = 0
if 'test_config' not in st.session_state: st.session_state.test_config = {}
if 'clear_counter' not in st.session_state: st.session_state.clear_counter = 0 

# Challenge-mode room/domain state (used by page_challenge + the shared test_execution flow)
if 'current_room_code' not in st.session_state: st.session_state.current_room_code = None
if 'challenge_view' not in st.session_state: st.session_state.challenge_view = 'menu'
if 'challenge_selected_domains' not in st.session_state: st.session_state.challenge_selected_domains = []
if 'challenge_custom_topics' not in st.session_state: st.session_state.challenge_custom_topics = []
if 'challenge_test_start_time' not in st.session_state: st.session_state.challenge_test_start_time = 0
if 'room_result_submitted' not in st.session_state: st.session_state.room_result_submitted = False

ui_pages.inject_css()

# SIDEBAR & NAVIGATION (Professional Look)
if st.session_state.username is not None and st.session_state.page not in ['landing', 'login']:
    is_testing = (st.session_state.page == 'dashboard' and st.session_state.dashboard_step == 'test_execution')
    
    if not is_testing:
        with st.sidebar:
            # 🎯 NEW PRO AVATAR IN SIDEBAR (Database Fetch Logic)
            conn = database.get_connection()
            c = conn.cursor()
            c.execute("SELECT profile_pic FROM users WHERE username = ?", (st.session_state.username,))
            row = c.fetchone()
            conn.close()
            
            # Check if DB has a saved URL, else generate the default unique one
            if row and row[0] and row[0].startswith("http"):
                avatar_url = row[0]
            else:
                avatar_url = ui_pages.get_avatar_url(st.session_state.username, style="micah")
            
            c1, c2 = st.columns([1, 3])
            with c1:
                st.markdown(f'<img src="{avatar_url}" width="50" style="border-radius: 50%; border: 2px solid #3b82f6; background: rgba(255,255,255,0.05);">', unsafe_allow_html=True)
            with c2:
                st.markdown(f"<h3 style='margin-top: 10px; font-size: 1.1rem;'>{st.session_state.username}</h3>", unsafe_allow_html=True)
            
            st.write("---")
            st.markdown("### 🧭 Navigation")
            
            # 🎯 NEW PROFESSIONAL BUTTONS
            if st.button("Overview", use_container_width=True): ui_pages.navigate_to('home')
            if st.button("Mock Assessments", use_container_width=True): ui_pages.navigate_to('dashboard')
            if st.button("Live Contests", use_container_width=True): ui_pages.navigate_to('challenge')
            if st.button("Notes & Saved Questions", use_container_width=True): ui_pages.navigate_to('vault')
            if st.button("Account", use_container_width=True): ui_pages.navigate_to('profile')
            
            st.write("---")
            if st.button("Logout", use_container_width=True):
                st.session_state.username = None
                ui_pages.navigate_to('landing')

# PAGE ROUTING ENGINE
if st.session_state.page == 'landing': ui_pages.page_landing()
elif st.session_state.page == 'login': ui_pages.page_login()
elif st.session_state.page == 'home': ui_pages.page_home()
elif st.session_state.page == 'dashboard': ui_pages.page_dashboard()
elif st.session_state.page == 'profile': ui_pages.page_profile()
elif st.session_state.page == 'vault': ui_pages.page_vault()
elif st.session_state.page == 'challenge': ui_pages.page_challenge()

# Fallbacks for old pages (just in case they are needed in the vault later)
elif st.session_state.page == 'history': ui_pages.page_history()
elif st.session_state.page == 'saved_questions': ui_pages.page_saved_questions()