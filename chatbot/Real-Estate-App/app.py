import streamlit as st
import pandas as pd
from databricks import sql
import google.generativeai as genai

st.set_page_config(page_title="مستشارك العقاري", page_icon="🏢", layout="centered")

def inject_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;900&display=swap');
    
    * { font-family: 'Cairo', sans-serif !important; }
    
    [data-testid="stAppViewContainer"] {
        background-image: url("https://images.unsplash.com/photo-1600607687920-4e2a09cf159d?ixlib=rb-4.0.3&auto=format&fit=crop&w=1920&q=80");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }
    .stApp { direction: rtl; background: transparent !important; }
    
    [data-testid="stHeader"] {
        background-color: transparent !important;
        box-shadow: none !important;
    }
    [data-testid="stToolbar"], [data-testid="collapsedControl"] { display: none !important; }
    
    [data-testid="stBottom"], [data-testid="stBottom"] > * {
        background: transparent !important;
    }
    
    .hero-box {
        background: linear-gradient(135deg, #0f2027 0%, #203a43 50%, #2c5364 100%);
        padding: 35px 20px;
        border-radius: 20px;
        text-align: center !important;
        margin-bottom: 30px;
        box-shadow: 0 10px 20px rgba(0,0,0, 0.3);
    }
    
    .hero-box h1, .hero-box h1 span, .hero-box h1 * {
        color: #ffffff !important;
        font-weight: 900 !important;
        font-size: 2.8rem !important;
        text-align: center !important;
    }
    .hero-box p, .hero-box p span, .hero-box p * {
        color: #e0f2f1 !important;
        font-size: 1.2rem !important;
        text-align: center !important;
    }
    
    [data-testid="stChatInput"] {
        background-color: rgba(255, 255, 255, 0.95) !important;
        border-radius: 25px !important;
        border: 2px solid #2c5364 !important;
        box-shadow: 0 10px 20px rgba(0,0,0,0.1) !important;
        padding: 5px !important;
        direction: rtl;
    }
    [data-testid="stChatInput"] div, [data-testid="stChatInput"] textarea {
        background-color: transparent !important;
        color: #000000 !important;
        -webkit-text-fill-color: #000000 !important;
        font-weight: 600 !important;
    }
    [data-testid="stChatInput"] textarea::placeholder {
        color: #666666 !important;
        -webkit-text-fill-color: #666666 !important;
    }
    [data-testid="stChatInput"] svg { fill: #2c5364 !important; color: #2c5364 !important; }
    
    .block-container {
        background: rgba(255, 255, 255, 0.45) !important; 
        backdrop-filter: blur(25px) !important;
        -webkit-backdrop-filter: blur(25px) !important;
        border-radius: 30px !important;
        padding: 30px 20px !important;
        margin-top: 20px !important;
        margin-bottom: 80px !important;
        box-shadow: 0 15px 50px rgba(0,0,0,0.2) !important;
        border: 1px solid rgba(255, 255, 255, 0.6) !important;
    }
    
    p, div, span, label, li { text-align: right; color: #1a1a1a; }
    
    [data-testid="stChatMessage"] {
        background-color: rgba(255, 255, 255, 0.85) !important;
        border-radius: 16px;
        padding: 20px;
        border: 1px solid rgba(255,255,255,0.5);
        box-shadow: 0 4px 10px rgba(0,0,0,0.05);
        margin-bottom: 15px;
    }
    
    .stAlert {
        background-color: rgba(230, 245, 255, 0.8) !important;
        border: 1px solid #203a43 !important;
        border-radius: 16px !important;
    }
    .stAlert p { color: #1a1a1a !important; font-weight: 600; }
    
    /* 🔴 الحل النهائي للنقط السوداء عشان تدخل جوه الصندوق الأزرق */
    .stAlert ul {
        padding-right: 25px !important;
        padding-left: 0 !important;
    }
    .stAlert li {
        list-style-position: inside !important;
    }
    
    [data-testid="stDataFrame"] { direction: ltr; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# App configs & API keys
GEMINI_KEY = ""
DB_HOST = "dbc-58a1a3ba-94fc.cloud.databricks.com"
DB_PATH = "/sql/1.0/warehouses/4d72dcee6968660b"
DB_TOKEN = ""

genai.configure(api_key=GEMINI_KEY)

system_instruction = """
أنت محلل بيانات. حول أسئلة المستخدم إلى Databricks SQL.
مخطط قاعدة البيانات:
1. `gold_df`: title (STRING), location (STRING), price (DOUBLE), area (DOUBLE), property_type (STRING), price_per_sqm (DOUBLE).
2. `gold_location_summary`: location (STRING), total_properties (BIGINT), avg_price (DOUBLE), avg_area (DOUBLE), avg_price_per_sqm (DOUBLE), max_price (DOUBLE), min_price (DOUBLE).
3. `gold_type_summary`: property_type (STRING), total_properties (BIGINT), avg_price_per_type (DOUBLE), avg_area_per_type (DOUBLE).
4. `gold_area_segment`: area_segment (STRING), total_properties (BIGINT), avg_price (DOUBLE).
5. `gold_top_expensive`: title (STRING), location (STRING), price (DOUBLE), area (DOUBLE).

القواعد:
- أرجع كود SQL فقط.
- استخدم الجداول التجميعية قدر الإمكان.
- استخدم ILIKE.
- استخدم SQL Aliases.
- تجنب استخدام order واستخدم orders.
"""

def text_to_sql(prompt):
    try:
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction)
        response = model.generate_content(prompt)
        return response.text.replace("```sql", "").replace("```", "").strip()
    except Exception as e:
        print(f"Error generating SQL: {e}")
        return None

def execute_query(query):
    try:
        with sql.connect(server_hostname=DB_HOST, http_path=DB_PATH, access_token=DB_TOKEN) as conn:
            return pd.read_sql(query, conn)
    except Exception as e:
        print(f"Database error: {e}")
        return None

# --- App UI Rendering ---
inject_custom_css()

st.markdown("""
<div class="hero-box">
    <h1>مستشارك العقاري الذكي ✦</h1>
    <p>بندور معاك على بيت أحلامك.. أسعار، مساحات، وأماكن في خطوة واحدة</p>
</div>
""", unsafe_allow_html=True)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    
    st.info("""
    **أهلاً بيك!** 👋  
    أنا هنا عشان أسهل عليك رحلة البحث عن عقار. مفيش داعي تلف كتير، قولي بس بتدور على إيه وميزانيتك كام، وأنا هجيبلك أفضل الخيارات المتاحة فوراً.
    
    💡 **جرب تسألني ببساطة كده:**
    * "عايز شقة في التجمع مساحتها أكبر من 150 متر وسعرها حنين"
    * "إيه أرخص الفيلات المتاحة في مدينة أكتوبر؟"
    * "هاتلي 5 شقق في زايد سعرهم أقل من 3 مليون جنيه"
    """)

for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], pd.DataFrame):
            st.dataframe(msg["content"], use_container_width=True)
        else:
            st.markdown(msg["content"])

user_query = st.chat_input("اكتب طلبك هنا... (مثال: شقة في التجمع بأقل من 2 مليون)")

if user_query:
    st.chat_message("user").markdown(user_query)
    st.session_state.chat_history.append({"role": "user", "content": user_query})

    with st.chat_message("assistant"):
        with st.spinner("بندور على أفضل الخيارات المناسبة لطلبك..."):
            sql_query = text_to_sql(user_query)
            
            if sql_query:
                data = execute_query(sql_query)
                
                if data is not None and not data.empty:
                    st.dataframe(data, use_container_width=True)
                    st.session_state.chat_history.append({"role": "assistant", "content": data})
                else:
                    err_msg = "للأسف ملقيناش عقارات مطابقة للمواصفات دي حالياً."
                    st.warning(err_msg)
                    st.session_state.chat_history.append({"role": "assistant", "content": err_msg})