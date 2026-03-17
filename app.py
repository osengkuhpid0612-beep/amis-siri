import streamlit as st
import pandas as pd
import os
import requests
from io import BytesIO

# 1. 設定
st.set_page_config(page_title="海岸阿美語 Siri", layout="wide")

# 讀取金鑰 (這裡假設你已經在 Secrets 設定好)
ELEVENLABS_API_KEY = st.secrets.get("ELEVENLABS_API_KEY", "")

# 2. 角色設定
CHARACTER = {
    'pulaw': {'name': 'Pulaw', 'voice_id': 'JBFqnCBsd6RMkjVB3PnJ', 'emoji': '👨'},
    'panay': {'name': 'Panay', 'voice_id': 'EXAVITQu4EsNXjluf0k5', 'emoji': '👩'}
}

# 3. 側邊欄
with st.sidebar:
    st.header("🎭 角色切換")
    char_key = st.radio("選擇老師", ['pulaw', 'panay'], format_func=lambda x: f"{CHARACTER[x]['emoji']} {CHARACTER[x]['name']}")
    st.markdown("---")
    st.info("💡 提示：優先播放官方真人音檔，若無音檔才使用 AI 合成聲。")

# 4. 讀取語料庫
@st.cache_data
def load_data():
    return pd.read_csv('coastal_amis_siri_lessons.csv')

df = load_data()

# 5. 主介面
st.title(f"🗣️ 族語 Siri - {CHARACTER[char_key]['name']} 老師")
user_input = st.text_input("輸入想說的話：", placeholder="例如：你好、早安、去哪裡...")

if user_input:
    # A. 先在 CSV 找關鍵字
    match = df[df['chinese_translation'].str.contains(user_input, na=False) | 
               df['amis_text'].str.contains(user_input, na=False)].head(1)
    
    if not match.empty:
        amis_text = match.iloc[0]['amis_text']
        official_audio = match.iloc[0]['audio_url']
        
        st.success(f"✅ 找到標準教學：{amis_text}")
        
        # 優先用官方音檔 (不扣錢)
        if pd.notna(official_audio) and str(official_audio).startswith('http'):
            st.write("🎵 播放官方真人音檔：")
            st.audio(official_audio)
        else:
            st.warning("⚠️ 此句無官方音檔，嘗試使用 AI 合成...")
            # 這裡可以接 ElevenLabs 生成邏輯...
    else:
        st.error("🤔 阿公還沒學過這句，但我可以教你類似的！")
        st.write("試試看這些句子：", df['chinese_translation'].sample(3).tolist())
