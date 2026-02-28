import streamlit as st
import sympy as sp
import math
import os
import base64
import json
from pathlib import Path
import google.generativeai as genai
from streamlit_google_auth import Authenticate
from dotenv import load_dotenv
import auth_db
from scraper import scrape_website  # Import the scraper function

# --- 1. INITIALIZATION & ENVIRONMENT ---
load_dotenv()
auth_db.init_db()  # Initialize the local user database
st.set_page_config(page_title="Bubloo Scientist | Pro Suite", page_icon="🔬", layout="wide")

# Google OAuth Setup (Using your provided credentials)
if 'authenticated' not in st.session_state:
    st.session_state['authenticated'] = False
if 'user_info' not in st.session_state:
    st.session_state['user_info'] = None

# Construct credentials from secrets
credentials_dict = {
    "web": {
        "client_id": st.secrets["google_oauth"]["client_id"],
        "project_id": st.secrets["google_oauth"]["project_id"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
        "client_secret": st.secrets["google_oauth"]["client_secret"],
        "redirect_uris": ["http://localhost:8501"],
        "javascript_origins": ["http://localhost:8501"]
    }
}

# Write credentials to a temporary file for the library to use
with open("google_credentials.json", "w") as f:
    json.dump(credentials_dict, f)

authenticator = Authenticate(
    secret_credentials_path='google_credentials.json',
    cookie_name='bubloo_scientist_auth',
    cookie_key='bubloo_auth_cookie_key',
    redirect_uri='http://localhost:8501',
)

# Gemini AI Setup
GEMINI_API_KEY = st.secrets.get("GEMINI_API_KEY", os.getenv('GEMINI_API_KEY'))
genai.configure(api_key=GEMINI_API_KEY)
PDF_DIR = Path(__file__).parent / 'knowledge_base'
PDF_DIR.mkdir(exist_ok=True)

# Model configuration
generation_config = {
    "temperature": 0.5,
    "top_p": 0.8,
    "top_k": 4,
    "max_output_tokens": 2048,
}

model = genai.GenerativeModel(
    model_name='gemini-2.5-flash',
    generation_config=generation_config
)

# --- 2. AI HELPER FUNCTIONS ---
def load_text_context():
    """Load text files from knowledge_base (team info, scraped content)"""
    text_context = ""
    try:
        txt_files = list(PDF_DIR.glob('*.txt'))
        for txt_path in txt_files:
            with open(txt_path, 'r', encoding='utf-8') as f:
                text_context += f"\n\n--- Source: {txt_path.name} ---\n{f.read()}"
    except Exception as e:
        return ""
    return text_context

# --- 3. LOGIN GATE ---
authenticator.check_authentification()

# Sync the library's 'connected' state with the app's 'authenticated' state
# But only if manual login hasn't already set it
if not st.session_state.get('authenticated'):
    st.session_state['authenticated'] = st.session_state.get('connected', False)

if not st.session_state.get('authenticated'):
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(
            """
            <div style="text-align: center; padding: 40px 0;">
                <h1 style="font-size: 3rem;">🔬</h1>
                <h1 style="margin-bottom: 10px;">Bubloo Scientist</h1>
                <p style="color: #8b949e; font-size: 1.2rem;">Your Advanced AI Research Companion</p>
                <hr style="border-color: #30363d; margin: 30px 0;">
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        tab_google, tab_manual = st.tabs(["🔒 Google Login", "📝 Standard Login"])
        
        with tab_google:
            st.info("Please sign in with Google to access the professional suite.")
            authenticator.login()
            
        with tab_manual:
            manual_mode = st.radio("Select Mode", ["Sign In", "Register"], horizontal=True, label_visibility="collapsed")
            
            if manual_mode == "Sign In":
                with st.form("login_form"):
                    username = st.text_input("Username")
                    password = st.text_input("Password", type="password")
                    submit_login = st.form_submit_button("Sign In", use_container_width=True)
                    
                    if submit_login:
                        user = auth_db.verify_user(username, password)
                        if user:
                            st.session_state['authenticated'] = True
                            st.session_state['user_info'] = user
                            st.rerun()
                        else:
                            st.error("Invalid username or password.")
                            
            elif manual_mode == "Register":
                with st.form("register_form"):
                    new_user = st.text_input("Choose Username")
                    full_name = st.text_input("Full Name")
                    new_pass = st.text_input("Password", type="password")
                    confirm_pass = st.text_input("Confirm Password", type="password")
                    submit_reg = st.form_submit_button("Create Account", use_container_width=True)
                    
                    if submit_reg:
                        if new_pass != confirm_pass:
                            st.error("Passwords do not match.")
                        elif len(new_pass) < 6:
                            st.error("Password must be at least 6 characters.")
                        elif not new_user:
                            st.error("Username is required.")
                        else:
                            # Register user in DB
                            success, msg = auth_db.register_user(new_user, new_pass, full_name)
                            if success:
                                st.success("Account created successfully! Please switch to 'Sign In' tab.")
                            else:
                                st.error(msg)
                                
    st.stop()

# --- 4. MAIN APP (AUTHENTICATED) ---
if st.session_state.get('authenticated'):
    # Sidebar Navigation
    with st.sidebar:
        col_user_icon, col_user_info = st.columns([1, 3])
        with col_user_icon:
            st.write("👤")
        with col_user_info:
            user_info = st.session_state.get('user_info', {})
            user_name = user_info.get('name', 'Scientist') if user_info else 'Scientist'
            st.write(f"**{user_name}**")
        
        if st.button("Log out"):
            # Check if it was a Google login (has connected=True from library)
            if st.session_state.get('connected'):
                authenticator.logout()
            else:
                # Manual logout
                for key in ['authenticated', 'user_info', 'connected']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
        st.markdown('<div style="height: 20px;"></div>', unsafe_allow_html=True)
        
        st.markdown("### 🧭 Navigation")
        topic = st.radio("Select Module", 
            ["AI Lab Assistant", "Site Info Guide", "Geometry (2D & 3D)", "Circle Equations", "Algebra & Polynomials", "Probability & Series", "Kinematics"],
            label_visibility="collapsed"
        )
        
        st.markdown("---")
        st.caption("© 2026 Bubloo Scientist Team\nProfessional Edition v2.5")

    # PROFESSIONAL CSS STYLING
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        .stApp {
            background-color: #0d1117;
            color: #c9d1d9;
        }

        section[data-testid="stSidebar"] {
            background-color: #161b22;
            border-right: 1px solid #30363d;
        }

        .res-card {
            background-color: #161b22;
            border: 1px solid #30363d;
            border-radius: 8px;
            padding: 24px;
            margin-top: 20px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        }

        .stButton>button {
            height: 3rem;
            width: 100%;
            background-color: #238636;
            color: white;
            font-size: 16px;
            font-weight: 600;
            border: 1px solid rgba(240, 246, 252, 0.1);
            border-radius: 6px;
            margin-top: 28px;
            transition: all 0.2s;
        }

        .stButton>button:hover {
            background-color: #2ea043;
            border-color: #2ea043;
            box-shadow: 0 0 0 3px rgba(46, 160, 67, 0.4);
        }

        h1, h2, h3 {
            color: #ffffff !important;
            font-weight: 700;
        }

        .stTextInput>div>div>input {
            background-color: #0d1117;
            color: #ffffff;
            border: 1px solid #30363d;
            border-radius: 6px;
        }

        .stTextInput>div>div>input:focus {
            border-color: #58a6ff;
            box-shadow: 0 0 0 3px rgba(88, 166, 255, 0.3);
        }
        
        .metric-container {
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: 10px;
            background: #21262d;
            border-radius: 8px;
            border: 1px solid #30363d;
        }
        .metric-value {
            font-size: 1.5rem;
            font-weight: bold;
            color: #58a6ff;
        }
        .metric-label {
            font-size: 0.9rem;
            color: #8b949e;
        }
        </style>
        """, unsafe_allow_html=True)

    # --- MODULE 1: AI LAB ASSISTANT ---
    if topic == "AI Lab Assistant":
        st.title("🤖 AI Lab Assistant")
        st.markdown("Analyze documents and get instant scientific answers.")
        
        # Automatic Scraping Logic
        target_url = "https://bublooscientist.com"
        scraped_file = PDF_DIR / "scraped_content.txt"
        
        # Check if we need to scrape (e.g., file doesn't exist or not scraped in this session)
        if 'scraped_session' not in st.session_state:
            st.session_state['scraped_session'] = False
            
        if not st.session_state['scraped_session'] and not scraped_file.exists():
             with st.spinner(f"Automatically scraping {target_url} for knowledge base..."):
                success, msg = scrape_website(target_url)
                if success:
                    st.success("Knowledge base updated from website!")
                    st.session_state['scraped_session'] = True
                    st.cache_data.clear()
                else:
                    st.warning(f"Automatic scraping failed: {msg}")
        
        # Display Knowledge Base Status
        txt_files = list(PDF_DIR.glob('*.txt'))
        with st.expander(f"📚 Knowledge Base Status ({len(txt_files)} text sources)", expanded=False):
            if txt_files:
                for t in txt_files:
                    st.text(f"📄 {t.name}")
            else:
                st.warning("No text sources found in knowledge_base directory.")

        st.markdown("---")
        
        with st.form("ai_query_form"):
            query = st.text_area("Research Query", placeholder="Enter your question here based on the knowledge base...", height=100)
            submit_btn = st.form_submit_button("Generate Analysis")

        if submit_btn and query:
            with st.spinner("🤖 Analyzing documents and generating response..."):
                try:
                    parts = []
                    # Only using text context now
                    system_context = f"""You are a helpful AI assistant for Bubloo Scientist website.
                    
                    Use the following Context to answer the user's question.
                    
                    --- Additional Context (Team Info, Website Content) ---
                    {load_text_context()}
                    
                    Answer questions PRIMARILY based on the provided Context.
                    If the information is NOT in the context, you can use general knowledge but mention it.
                    User question: {query}"""
                    
                    parts.append({'text': system_context})
                    response = model.generate_content(parts)
                    
                    st.markdown("### 💡 Analysis Result")
                    st.markdown(f'<div class="res-card">{response.text}</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Analysis Failed: {str(e)}")

    # --- MODULE 2: SITE INFO GUIDE ---
    elif topic == "Site Info Guide":
        st.title("🔬 Site Information Guide")
        st.markdown("Quickly find details about our team and how to reach us.")
        
        with st.container():
            col_search, col_btn = st.columns([4, 1])
            with col_search:
                query = st.text_input("Information Search", placeholder="Type 'team', 'contact', or 'hello'...", label_visibility="collapsed").lower()
            with col_btn:
                info_btn = st.button("Search", key="info_send", use_container_width=True)

        if info_btn and query:
            st.markdown('<div class="res-card">', unsafe_allow_html=True)
            if any(greet in query for greet in ["hi", "hello", "hey", "salam"]):
                st.success(f"👋 Hello {st.session_state['user_info'].get('given_name')}! I'm the Bubloo Scientist assistant. How can I help you?")
            elif "team" in query or "members" in query:
                st.markdown("### 👥 The Executive Team")
                st.markdown("""
                * **Abdur Rehman Siddiqui** - CEO
                * **Ayaan Hassan Khan** - Web Developer
                * **Saim Ahmed** - Social Media Manager
                * **Sadaat Furqan** - Marketer
                * **Muhammad Mustafa Khan** - Lead Designer
                * **Muhammad Huzaifa Khan** - Web Designer
                """)
            elif "contact" in query or "email" in query:
                st.markdown("### 📬 Contact Details")
                st.markdown("📧 **Email:** `bublooscientist2023@gmail.com`")
                st.markdown("🌐 **Website:** [bublooscientist.com](https://www.bublooscientist.com)")
            else:
                st.info("💡 Try searching for **'team'** or **'contact'**.")
            st.markdown('</div>', unsafe_allow_html=True)

    # --- MODULE 3: GEOMETRY (2D & 3D) ---
    elif topic == "Geometry (2D & 3D)":
        st.title("📐 Geometry Suite")
        st.markdown("Perform calculations on 2D and 3D geometric shapes.")
        
        tab1, tab2 = st.tabs(["🟦 2D Plane Geometry", "🧊 3D Solid Geometry"])
        with tab1:
            shape_2d = st.selectbox("Select 2D Shape", ["Circle", "Rectangle", "Triangle"])
            st.markdown("---")
            
            if shape_2d == "Circle":
                col_in, col_res = st.columns([1, 2])
                with col_in:
                    r = st.number_input("Radius", min_value=0.0, step=0.1)
                    calc = st.button("Calculate", key="2d_c", use_container_width=True)
                with col_res:
                    if calc:
                        c1, c2 = st.columns(2)
                        c1.markdown(f'<div class="metric-container"><div class="metric-label">Area</div><div class="metric-value">{math.pi*r**2:.4f}</div></div>', unsafe_allow_html=True)
                        c2.markdown(f'<div class="metric-container"><div class="metric-label">Circumference</div><div class="metric-value">{2*math.pi*r:.4f}</div></div>', unsafe_allow_html=True)
            
            elif shape_2d == "Rectangle":
                col_in, col_res = st.columns([1, 2])
                with col_in:
                    l = st.number_input("Length", min_value=0.0, step=0.1)
                    w = st.number_input("Width", min_value=0.0, step=0.1)
                    calc = st.button("Calculate", key="2d_r", use_container_width=True)
                with col_res:
                    if calc:
                        c1, c2 = st.columns(2)
                        c1.markdown(f'<div class="metric-container"><div class="metric-label">Area</div><div class="metric-value">{l*w:.4f}</div></div>', unsafe_allow_html=True)
                        c2.markdown(f'<div class="metric-container"><div class="metric-label">Perimeter</div><div class="metric-value">{2*(l+w):.4f}</div></div>', unsafe_allow_html=True)
            
            elif shape_2d == "Triangle":
                col_in, col_res = st.columns([1, 2])
                with col_in:
                    b = st.number_input("Base", min_value=0.0, step=0.1)
                    h = st.number_input("Height", min_value=0.0, step=0.1)
                    calc = st.button("Calculate", key="2d_t", use_container_width=True)
                with col_res:
                    if calc:
                        st.markdown(f'<div class="metric-container"><div class="metric-label">Area</div><div class="metric-value">{0.5*b*h:.4f}</div></div>', unsafe_allow_html=True)

        with tab2:
            shape_3d = st.selectbox("Select 3D Shape", ["Sphere", "Cube", "Cylinder"])
            st.markdown("---")
            
            if shape_3d == "Sphere":
                col_in, col_res = st.columns([1, 2])
                with col_in:
                    r3 = st.number_input("Radius", min_value=0.0, step=0.1, key="3d_s_r")
                    calc = st.button("Calculate", key="3d_s", use_container_width=True)
                with col_res:
                    if calc:
                        st.markdown(f'<div class="metric-container"><div class="metric-label">Volume</div><div class="metric-value">{(4/3)*math.pi*r3**3:.2f}</div></div>', unsafe_allow_html=True)
            
            elif shape_3d == "Cube":
                col_in, col_res = st.columns([1, 2])
                with col_in:
                    s = st.number_input("Side Length", min_value=0.0, step=0.1)
                    calc = st.button("Calculate", key="3d_cb", use_container_width=True)
                with col_res:
                    if calc:
                        st.markdown(f'<div class="metric-container"><div class="metric-label">Volume</div><div class="metric-value">{s**3:.2f}</div></div>', unsafe_allow_html=True)
            
            elif shape_3d == "Cylinder":
                col_in, col_res = st.columns([1, 2])
                with col_in:
                    rc = st.number_input("Radius", min_value=0.0, step=0.1, key="cyl_r")
                    hc = st.number_input("Height", min_value=0.0, step=0.1, key="cyl_h")
                    calc = st.button("Calculate", key="3d_cyl", use_container_width=True)
                with col_res:
                    if calc:
                        st.markdown(f'<div class="metric-container"><div class="metric-label">Volume</div><div class="metric-value">{math.pi*rc**2*hc:.2f}</div></div>', unsafe_allow_html=True)

    # --- MODULE 4: CIRCLE EQUATIONS ---
    elif topic == "Circle Equations":
        st.title("⭕ Circle Equation Solver")
        st.markdown("Generate standard circle equations from center and radius.")
        
        col_eq, col_input = st.columns([1, 1])
        with col_eq:
            st.info("Standard Form")
            st.latex(r"(x - a)^2 + (y - b)^2 = r^2")
        
        with col_input:
            c1, c2 = st.columns(2)
            a_v = c1.number_input("Center x (a)", step=0.1)
            b_v = c2.number_input("Center y (b)", step=0.1)
            r_v = st.number_input("Radius (r)", value=1.0, min_value=0.1, step=0.1)
            
            solve = st.button("Generate Equation", use_container_width=True)

        if solve:
            x, y = sp.symbols('x y')
            eq = sp.expand(sp.Eq((x - a_v)**2 + (y - b_v)**2, r_v**2))
            st.markdown("### Result")
            st.markdown('<div class="res-card" style="text-align: center;">', unsafe_allow_html=True)
            st.latex(sp.latex(eq))
            st.markdown('</div>', unsafe_allow_html=True)

    # --- MODULE 5: ALGEBRA & POLYNOMIALS ---
    elif topic == "Algebra & Polynomials":
        st.title("➗ Algebraic Engine")
        st.markdown("Factorize polynomials and find roots instantly.")
        
        col_in, col_act = st.columns([3, 1])
        with col_in:
            poly = st.text_input("Polynomial Expression", "x**2 - 5*x + 6", help="Use standard python syntax, e.g. x**2 for x squared.")
        with col_act:
            solve_btn = st.button("Analyze", use_container_width=True)

        if solve_btn:
            x = sp.symbols('x')
            try:
                expr = sp.sympify(poly)
                st.markdown("### Analysis Results")
                
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown('<div class="metric-container"><div class="metric-label">Factored Form</div>', unsafe_allow_html=True)
                    st.latex(sp.latex(sp.factor(expr)))
                    st.markdown('</div>', unsafe_allow_html=True)
                
                with c2:
                    st.markdown('<div class="metric-container"><div class="metric-label">Roots</div>', unsafe_allow_html=True)
                    roots = sp.solve(expr, x)
                    st.write(roots)
                    st.markdown('</div>', unsafe_allow_html=True)
            except Exception as e: 
                st.error(f"Syntax Error! Please use '*' for multiplication (e.g. 5*x). Details: {e}")

    # --- MODULE 6: PROBABILITY & SERIES ---
    elif topic == "Probability & Series":
        st.title("📊 Probability & Series")
        st.markdown("Calculate permutations and combinations for probability analysis.")
        
        col_op, col_val = st.columns([1, 2])
        with col_op:
            mode = st.radio("Operation", ["nCr (Combination)", "nPr (Permutation)"])
        
        with col_val:
            c1, c2 = st.columns(2)
            n = c1.number_input("Total Set (n)", min_value=0, value=5)
            r = c2.number_input("Selection (r)", min_value=0, value=2)
            calc_btn = st.button("Calculate", use_container_width=True)
            
        if calc_btn:
            if r > n:
                st.error("Selection (r) cannot be larger than Total Set (n).")
            else:
                res = math.comb(n, r) if mode == "nCr (Combination)" else math.perm(n, r)
                st.markdown(f'<div class="metric-container"><div class="metric-label">Result</div><div class="metric-value">{res}</div></div>', unsafe_allow_html=True)

    # --- MODULE 7: KINEMATICS ---
    elif topic == "Kinematics":
        st.title("🏃 Motion Calculator")
        st.markdown("Calculate velocity and displacement using kinematic equations.")
        
        with st.expander("Formula Sheet", expanded=True):
            st.latex(r"v = u + at \quad | \quad s = ut + \frac{1}{2}at^2")
        
        col_inputs, col_res = st.columns([1, 1])
        with col_inputs:
            u = st.number_input("Initial Velocity (u)", value=0.0)
            a = st.number_input("Acceleration (a)", value=9.8)
            t = st.number_input("Time (t)", value=1.0)
            calc = st.button("Calculate Motion", use_container_width=True)
        
        with col_res:
            if calc:
                v = u + a*t
                s = u*t + 0.5*a*t**2
                st.markdown(f'<div class="metric-container"><div class="metric-label">Final Velocity (v)</div><div class="metric-value">{v:.2f} m/s</div></div>', unsafe_allow_html=True)
                st.markdown('<div style="height: 10px"></div>', unsafe_allow_html=True)
                st.markdown(f'<div class="metric-container"><div class="metric-label">Displacement (s)</div><div class="metric-value">{s:.2f} m</div></div>', unsafe_allow_html=True)