import streamlit as st
import pandas as pd
import os
import requests
from io import BytesIO
from datetime import datetime

# ==================== 1. 基本配置 ====================
st.set_page_config(page_title="族語 Siri - 角色版", page_icon="🗣️", layout="wide")

# ElevenLabs 鑰匙讀取
try:
    ELEVENLABS_API_KEY = st.secrets["ELEVENLABS_API_KEY"]
except:
    ELEVENLABS_API_KEY = ""

CHARACTER_CONFIG = {
    'pulaw': {'name': 'Pulaw', 'voice_id': 'JBFqnCBsd6RMkjVB3PnJ', 'emoji': '👨', 'color': '#FF6B6B'},
    'panay': {'name': 'Panay', 'voice_id': 'EXAVITQu4EsNXjluf0k5', 'emoji': '👩', 'color': '#4ECDC4'}
}

# ==================== 2. 側邊欄 ====================
with st.sidebar:
    st.header("🎭 角色選擇")
    char_key = st.radio("選擇老師", ['pulaw', 'panay'], 
                        format_func=lambda x: f"{CHARACTER_CONFIG[x]['emoji']} {CHARACTER_CONFIG[x]['name']}")
    
    st.markdown("---")
    app_mode = st.radio("選擇功能", ["💬 實時對話", "📚 課程查詢", "✏️ 修正管理"])
    
    if not ELEVENLABS_API_KEY:
        st.warning("⚠️ 請在 Streamlit Secrets 設定 API Key")
    else:
        st.success("✅ 語音系統已就緒")

# ==================== 3. 核心功能函數 ====================
def synthesize_speech(text, voice_id):
    if not ELEVENLABS_API_KEY: return None
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    data = {"text": text, "model_id": "eleven_multilingual_v2"}
    res = requests.post(url, json=data, headers=headers)
    return BytesIO(res.content) if res.status_code == 200 else None

# ==================== 4. 主要畫面 ====================
st.title(f"🗣️ 族語 Siri - {CHARACTER_CONFIG[char_key]['name']} 模式")

if app_mode == "💬 實時對話":
    # 載入語料庫
    if os.path.exists('coastal_amis_siri_lessons.csv'):
        df = pd.read_csv('coastal_amis_siri_lessons.csv')
        
        # --- 這裡就是你的門面！確保它在最外面 ---
        user_input = st.text_input("想跟老師說什麼？(中文或族語)", placeholder="例如：你好 或 Nga'ay ho")
        
        if user_input:
            # 簡單搜尋邏輯
            match = df[df['chinese_translation'].str.contains(user_input, na=False) | 
                       df['amis_text'].str.contains(user_input, na=False)].head(1)
            
            if not match.empty:
                amis_res = match.iloc[0]['amis_text']
                chn_res = match.iloc[0]['chinese_translation']
                
                st.info(f"💡 找到對應族語：{amis_res}")
                
                # 語音生成
                with st.spinner('老師正在開口...'):
                    audio = synthesize_speech(amis_res, CHARACTER_CONFIG[char_key]['voice_id'])
                    if audio:
                        st.audio(audio, format='audio/mp3')
                    else:
                        st.error("語音生成失敗，請檢查 API 額度")
            else:
                st.warning("阿公還沒學過這句，換一聲試試？")
    else:
        st.error("❌ 找不到 coastal_amis_siri_lessons.csv，請確認 GitHub 檔案名稱正確。")

elif app_mode == "📚 課程查詢":
    if os.path.exists('coastal_amis_siri_lessons.csv'):
        df = pd.read_csv('coastal_amis_siri_lessons.csv')
        st.dataframe(df)

elif app_mode == "✏️ 修正管理":
    st.subheader("教老師說正確的族語")
    with st.form("correction_form"):
        wrong = st.text_input("老師說錯的")
        right = st.text_input("應該要說的")
        if st.form_submit_state("提交修正"):
            st.success("收到了！我會努力學習。")
