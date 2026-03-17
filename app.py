#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
族語 Siri - 角色化升級版
海岸阿美語（'Amis-Hay'an）養成 App

功能：
- 角色選擇（Pulaw 男聲 vs Panay 女聲）
- 人格化回覆邏輯
- ElevenLabs API 語音合成
- 實時語音生成和播放
- 修正回報與進化日誌
"""

import streamlit as st
import pandas as pd
import json
import os
from datetime import datetime
from difflib import SequenceMatcher
import requests
from io import BytesIO

# 嘗試導入 streamlit-mic-recorder
try:
    from streamlit_mic_recorder import mic_recorder
    HAS_MIC_RECORDER = True
except ImportError:
    HAS_MIC_RECORDER = False

# ==================== 角色配置（固化） ====================
CHARACTER_CONFIG = {
    'pulaw': {
        'name': 'Pulaw',
        'gender': '男',
        'voice_id': 'JBFqnCBsd6RMkjVB3PnJ',  # ElevenLabs 男聲 ID
        'emoji': '👨',
        'personality': '豪爽、直率、充滿朝氣',
        'tone_prefix': '（語氣豪爽）',
        'tone_description': '直接、有力、充滿自信',
        'color': '#FF6B6B',
        'greeting_style': '熱情、直接',
        'system_prompt': '你是 Pulaw，一位豪爽、直率、充滿朝氣的族語老師。你的回覆應該直接、有力、充滿自信。使用熱情、直接的問候風格。'
    },
    'panay': {
        'name': 'Panay',
        'gender': '女',
        'voice_id': 'EXAVITQu4EsNXjluf0k5',  # ElevenLabs 女聲 ID
        'emoji': '👩',
        'personality': '溫柔、親切、細心',
        'tone_prefix': '（語氣溫柔）',
        'tone_description': '柔和、親切、耐心',
        'color': '#4ECDC4',
        'greeting_style': '溫暖、親切',
        'system_prompt': '你是 Panay，一位溫柔、親切、細心的族語老師。你的回覆應該柔和、親切、耐心。使用溫暖、親切的問候風格。'
    }
}

# ElevenLabs API 配置（使用 st.secrets）
def get_elevenlabs_api_key():
    """從 st.secrets 讀取 ElevenLabs API Key"""
    try:
        return st.secrets["ELEVENLABS_API_KEY"]
    except (KeyError, FileNotFoundError):
        return os.getenv('ELEVENLABS_API_KEY', '')

ELEVENLABS_API_KEY = get_elevenlabs_api_key()
ELEVENLABS_API_URL = 'https://api.elevenlabs.io/v1'

# ==================== 設定頁面 ====================
st.set_page_config(
    page_title="族語 Siri - 角色版",
    page_icon="🗣️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 自訂 CSS 樣式
st.markdown("""
    <style>
    .main {
        padding: 2rem;
    }
    .stButton > button {
        width: 100%;
        padding: 0.75rem;
        font-size: 1rem;
        font-weight: bold;
    }
    .character-card {
        padding: 1.5rem;
        border-radius: 0.75rem;
        border: 3px solid;
        text-align: center;
        margin: 1rem 0;
    }
    .character-card.active {
        box-shadow: 0 0 20px rgba(0, 0, 0, 0.2);
    }
    .amis-text {
        font-size: 1.8rem;
        font-weight: bold;
        padding: 1.5rem;
        background-color: #f8f9fa;
        border-radius: 0.5rem;
        border-left: 5px solid #e74c3c;
        text-align: center;
    }
    .chinese-text {
        font-size: 1.4rem;
        color: #2c3e50;
        padding: 1.5rem;
        background-color: #ecf0f1;
        border-radius: 0.5rem;
        border-left: 5px solid #3498db;
        text-align: center;
    }
    .dialogue-box {
        padding: 1.2rem;
        margin: 1rem 0;
        border-radius: 0.5rem;
    }
    .user-dialogue {
        background-color: #d4edda;
        border-left: 5px solid #28a745;
    }
    .ai-dialogue {
        background-color: #d1ecf1;
        border-left: 5px solid #17a2b8;
    }
    .character-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 1rem;
        font-weight: bold;
        color: white;
        margin: 0.25rem;
    }
    .pulaw-badge {
        background-color: #FF6B6B;
    }
    .panay-badge {
        background-color: #4ECDC4;
    }
    .personality-text {
        font-style: italic;
        color: #666;
        font-size: 0.9rem;
    }
    .audio-player {
        padding: 1rem;
        background-color: #fff3cd;
        border-radius: 0.5rem;
        margin: 1rem 0;
    }
    </style>
""", unsafe_allow_html=True)

# 初始化 session state
if 'dialogue_history' not in st.session_state:
    st.session_state.dialogue_history = []

if 'selected_character' not in st.session_state:
    st.session_state.selected_character = 'pulaw'

if 'correction_log' not in st.session_state:
    st.session_state.correction_log = []

# ==================== 側邊欄配置 ====================
with st.sidebar:
    st.header("🎭 角色選擇")
    st.markdown("---")
    
    # 角色選擇
    character_choice = st.radio(
        "選擇您的族語老師",
        ['pulaw', 'panay'],
        format_func=lambda x: f"{CHARACTER_CONFIG[x]['emoji']} {CHARACTER_CONFIG[x]['name']} ({CHARACTER_CONFIG[x]['gender']}聲)",
        key='character_radio'
    )
    
    st.session_state.selected_character = character_choice
    
    # 顯示選中角色的信息
    selected_char = CHARACTER_CONFIG[character_choice]
    
    st.markdown(f"""
    <div style="padding: 1rem; background-color: {selected_char['color']}20; border-radius: 0.5rem; border-left: 5px solid {selected_char['color']};">
    <h3>{selected_char['emoji']} {selected_char['name']}</h3>
    <p><strong>性格：</strong> {selected_char['personality']}</p>
    <p><strong>語氣：</strong> {selected_char['tone_description']}</p>
    <p><strong>問候風格：</strong> {selected_char['greeting_style']}</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.header("📋 應用設定")
    
    app_mode = st.radio(
        "選擇功能",
        ["💬 實時對話", "📚 課程查詢", "✏️ 修正管理", "📊 統計分析"],
        help="選擇要使用的功能"
    )
    
    st.markdown("---")
    
    # ElevenLabs API 狀態
    st.subheader("🔧 API 狀態")
    if ELEVENLABS_API_KEY:
        st.success("✅ ElevenLabs API 已配置")
    else:
        st.warning("⚠️ ElevenLabs API 未配置")
        st.info("💡 請設定 ELEVENLABS_API_KEY 環境變數或在 .streamlit/secrets.toml 中配置")

# ==================== 輔助函數 ====================

@st.cache_data
def load_data():
    """載入 CSV 資料"""
    if os.path.exists('coastal_amis_siri_lessons.csv'):
        df = pd.read_csv('coastal_amis_siri_lessons.csv')
        return df
    else:
        st.error("❌ 找不到 CSV 檔案！")
        return None

@st.cache_data
def load_dialogue_contexts():
    """載入情境對話庫"""
    if os.path.exists('amis_dialogue_contexts.json'):
        with open('amis_dialogue_contexts.json', 'r', encoding='utf-8') as f:
            return json.load(f)
    else:
        return None

def create_lookup_dict(df):
    """建立中文到阿美語的對應字典"""
    lookup = {}
    for _, row in df.iterrows():
        chinese = row['chinese_translation'].strip()
        amis = row['amis_text'].strip()
        audio = row['audio_url']
        lesson_id = row['lesson_id']
        
        lookup[chinese] = {
            'amis': amis,
            'audio_url': audio,
            'lesson_id': lesson_id
        }
    
    return lookup

def create_amis_to_chinese_dict(df):
    """建立阿美語到中文的對應字典"""
    lookup = {}
    for _, row in df.iterrows():
        amis = row['amis_text'].strip()
        chinese = row['chinese_translation'].strip()
        audio = row['audio_url']
        lesson_id = row['lesson_id']
        
        lookup[amis] = {
            'chinese': chinese,
            'audio_url': audio,
            'lesson_id': lesson_id
        }
    
    return lookup

def fuzzy_match(input_text, candidates, threshold=0.6):
    """模糊匹配輸入文本與候選項"""
    best_match = None
    best_ratio = 0
    
    for candidate in candidates:
        ratio = SequenceMatcher(None, input_text.lower(), candidate.lower()).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
            best_match = candidate
    
    if best_ratio >= threshold:
        return best_match, best_ratio
    return None, best_ratio

def identify_context(text, dialogue_contexts):
    """識別輸入文本的情境"""
    if dialogue_contexts is None:
        return 'other'
    
    text_lower = text.lower()
    
    for context_type, items in dialogue_contexts.items():
        for item in items:
            chinese = item['chinese'].lower()
            amis = item['amis'].lower()
            
            if text_lower in chinese or text_lower in amis:
                return context_type
    
    return 'other'

def generate_personality_response(base_response, character_name):
    """根據角色生成人格化回覆"""
    character = CHARACTER_CONFIG[character_name]
    
    if character_name == 'pulaw':
        # Pulaw 的豪爽風格
        personality_markers = {
            '我理解了': '我明白了！',
            '好的': '沒問題！',
            '謝謝': '謝謝你！',
            '請': '來吧！',
            '對不起': '我知道了！',
        }
    else:  # panay
        # Panay 的溫柔風格
        personality_markers = {
            '我理解了': '我明白了呢...',
            '好的': '好的喔...',
            '謝謝': '謝謝你呢...',
            '請': '請慢慢來...',
            '對不起': '沒關係的...',
        }
    
    response = base_response
    for key, value in personality_markers.items():
        if key in response:
            response = response.replace(key, value)
    
    return response

def synthesize_speech(text, character_name):
    """使用 ElevenLabs API 合成語音"""
    if not ELEVENLABS_API_KEY:
        st.warning("⚠️ ElevenLabs API 未配置，無法生成語音")
        return None
    
    character = CHARACTER_CONFIG[character_name]
    voice_id = character['voice_id']
    
    try:
        url = f"{ELEVENLABS_API_URL}/text-to-speech/{voice_id}"
        
        headers = {
            "xi-api-key": ELEVENLABS_API_KEY,
            "Content-Type": "application/json"
        }
        
        data = {
            "text": text,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.75
            }
        }
        
        response = requests.post(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return BytesIO(response.content)
        else:
            st.error(f"❌ 語音合成失敗：{response.status_code}")
            return None
    
    except Exception as e:
        st.error(f"❌ 語音合成錯誤：{str(e)}")
        return None

def generate_amis_response(user_input, lookup_dict, amis_lookup, dialogue_contexts, character_name):
    """生成 AI 族語回覆（包含人格化）"""
    
    is_amis_input = any(char in user_input for char in ["'", "^", "a", "i", "u", "e", "o"])
    
    # 精確匹配 - 族語優先
    if is_amis_input and user_input in amis_lookup:
        meaning = amis_lookup[user_input]['chinese']
        audio_url = amis_lookup[user_input]['audio_url']
        context = identify_context(meaning, dialogue_contexts)
        
        # 找相關回覆
        if context in dialogue_contexts and dialogue_contexts[context]:
            follow_up = dialogue_contexts[context][0]
            response = follow_up['amis']
        else:
            response = '我理解了。'
        
        return {
            'type': 'exact_match_amis',
            'user_meaning': meaning,
            'response': response,
            'user_audio_url': audio_url,
            'context': context,
            'confidence': '100%'
        }
    
    # 精確匹配 - 中文
    if user_input in lookup_dict:
        return {
            'type': 'exact_match_chinese',
            'response': lookup_dict[user_input]['amis'],
            'user_audio_url': '',
            'context': identify_context(user_input, dialogue_contexts),
            'confidence': '100%'
        }
    
    # 模糊匹配 - 族語優先
    if is_amis_input:
        all_amis = list(amis_lookup.keys())
        matched_amis, ratio = fuzzy_match(user_input, all_amis)
        
        if matched_amis:
            meaning = amis_lookup[matched_amis]['chinese']
            context = identify_context(meaning, dialogue_contexts)
            
            if context in dialogue_contexts and dialogue_contexts[context]:
                follow_up = dialogue_contexts[context][0]
                response = follow_up['amis']
            else:
                response = '我理解了。'
            
            return {
                'type': 'fuzzy_match_amis',
                'user_meaning': meaning,
                'response': response,
                'user_audio_url': amis_lookup[matched_amis]['audio_url'],
                'context': context,
                'confidence': f"{ratio*100:.1f}%"
            }
    
    # 模糊匹配 - 中文
    all_chinese = list(lookup_dict.keys())
    matched_chinese, ratio = fuzzy_match(user_input, all_chinese)
    
    if matched_chinese:
        return {
            'type': 'fuzzy_match_chinese',
            'response': lookup_dict[matched_chinese]['amis'],
            'user_audio_url': '',
            'context': identify_context(matched_chinese, dialogue_contexts),
            'confidence': f"{ratio*100:.1f}%"
        }
    
    # 無法匹配
    return {
        'type': 'no_match',
        'response': '抱歉，我還不認識這個句子。',
        'user_audio_url': '',
        'context': 'other',
        'confidence': '0%'
    }

# ==================== 主要內容 ====================

# 頁面標題
st.title("🗣️ 族語 Siri - 角色版")
st.markdown("---")

# 載入資料
df = load_data()
dialogue_contexts = load_dialogue_contexts()

if df is not None and dialogue_contexts is not None:
    lookup_dict = create_lookup_dict(df)
    amis_lookup = create_amis_to_chinese_dict(df)
    
    selected_char = CHARACTER_CONFIG[st.session_state.selected_character]
    
    # ==================== 實時對話模式 ====================
    if app_mode == "💬 實時對話":
        st.header(f"💬 與 {selected_char['emoji']} {selected_char['name']} 對話")
        st.markdown(f"<p class='personality-text'>{selected_char['personality']}</p>", unsafe_allow_html=True)
        st.markdown("---")
        
        # 對話歷史顯示
        if st.session_state.dialogue_history:
            st.subheader("📝 對話記錄")
            for idx, dialogue in enumerate(st.session_state.dialogue_history):
                if dialogue['type'] == 'user':
                    st.markdown(f"""
                    <div class="dialogue-box user-dialogue">
                    <strong>👤 您：</strong> {dialogue['text']}<br/>
                    <small>🏷️ {dialogue.get('context', 'other')} | 信心度：{dialogue.get('confidence', '?')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if dialogue.get('audio_url'):
                        st.audio(dialogue['audio_url'], format='audio/mp3')
                
                else:  # AI 回覆
                    badge_class = 'pulaw-badge' if st.session_state.selected_character == 'pulaw' else 'panay-badge'
                    st.markdown(f"""
                    <div class="dialogue-box ai-dialogue">
                    <strong>{selected_char['emoji']} {selected_char['name']}：</strong> {dialogue['text']}<br/>
                    <small><span class="character-badge {badge_class}">{selected_char['name']}</span> 🏷️ {dialogue.get('context', 'other')}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if dialogue.get('audio_url'):
                        st.audio(dialogue['audio_url'], format='audio/mp3')
        
        st.markdown("---")
        
        # 語音輸入區
        st.subheader("🎤 語音輸入")
        
        user_input = st.text_input(
            "輸入族語或中文",
            placeholder="例如：Talacowa kiso? 或 你要去哪裡？",
            label_visibility="collapsed"
        )
        
        if st.button("📤 發送", use_container_width=True):
            if user_input:
                user_input = user_input.strip()
                context = identify_context(user_input, dialogue_contexts)
                
                # 添加用戶輸入
                st.session_state.dialogue_history.append({
                    'type': 'user',
                    'text': user_input,
                    'context': context,
                    'timestamp': datetime.now().isoformat(),
                    'audio_url': ''
                })
                
                # 生成 AI 回覆
                ai_response = generate_amis_response(user_input, lookup_dict, amis_lookup, dialogue_contexts, st.session_state.selected_character)
                
                # 人格化回覆
                personality_response = generate_personality_response(ai_response['response'], st.session_state.selected_character)
                
                # 語音合成
                audio_buffer = synthesize_speech(personality_response, st.session_state.selected_character)
                
                # 添加 AI 回覆
                st.session_state.dialogue_history.append({
                    'type': 'ai',
                    'text': personality_response,
                    'response_type': ai_response['type'],
                    'context': ai_response.get('context', 'other'),
                    'audio_url': audio_buffer if audio_buffer else '',
                    'timestamp': datetime.now().isoformat(),
                    'confidence': ai_response.get('confidence', '?'),
                    'character': st.session_state.selected_character
                })
                
                st.rerun()
        
        # 清除對話按鈕
        if st.button("🗑️ 清除對話記錄"):
            st.session_state.dialogue_history = []
            st.rerun()
    
    # ==================== 課程查詢模式 ====================
    elif app_mode == "📚 課程查詢":
        st.header("📚 課程查詢")
        st.markdown("按情境瀏覽所有課程")
        st.markdown("---")
        
        selected_context = st.selectbox(
            "選擇情境",
            list(dialogue_contexts.keys()),
            format_func=lambda x: f"{x.upper()} ({len(dialogue_contexts[x])} 個)"
        )
        
        st.markdown("---")
        
        items = dialogue_contexts[selected_context]
        
        if items:
            for item in items:
                with st.expander(f"📌 {item['chinese']}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown(f'<div class="amis-text">{item["amis"]}</div>', unsafe_allow_html=True)
                    
                    with col2:
                        st.markdown(f'<div class="chinese-text">{item["chinese"]}</div>', unsafe_allow_html=True)
                    
                    st.markdown("---")
                    st.write(f"**課程 ID：** {item.get('lesson_id', 'N/A')}")
        else:
            st.info("此情境下沒有課程")
    
    # ==================== 修正管理模式 ====================
    elif app_mode == "✏️ 修正管理":
        st.header("✏️ 修正管理")
        st.markdown("提交修正並記錄語境備註")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("❌ 錯誤的句子")
            error_amis = st.text_input(
                "錯誤的族語",
                placeholder="例如：Talacowa kiso?",
                key="error_amis"
            )
            error_chinese = st.text_input(
                "錯誤的中文",
                placeholder="例如：你要去哪裡？",
                key="error_chinese"
            )
        
        with col2:
            st.subheader("✅ 正確的句子")
            correct_amis = st.text_input(
                "正確的族語",
                placeholder="例如：Talacowa kiso?",
                key="correct_amis"
            )
            correct_chinese = st.text_input(
                "正確的中文",
                placeholder="例如：你要去哪裡？",
                key="correct_chinese"
            )
        
        st.markdown("---")
        
        st.subheader("💭 語境備註")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            mood = st.selectbox(
                "老師的心情/語氣",
                ["中立", "溫柔", "嚴肅", "開心", "著急", "其他"],
                key="mood"
            )
        
        with col2:
            context_type = st.selectbox(
                "使用情境",
                ["課堂教學", "日常交談", "糾正發音", "文化傳承", "其他"],
                key="context_type"
            )
        
        with col3:
            difficulty = st.selectbox(
                "難度等級",
                ["初級", "中級", "高級"],
                key="difficulty"
            )
        
        correction_reason = st.text_area(
            "修正說明",
            placeholder="請說明為什麼這個修正是正確的...",
            height=100,
            label_visibility="collapsed"
        )
        
        if st.button("📤 提交修正回報", use_container_width=True):
            if error_amis and error_chinese and correct_amis and correct_chinese:
                correction_record = {
                    'timestamp': datetime.now().isoformat(),
                    'error_amis': error_amis,
                    'error_chinese': error_chinese,
                    'correct_amis': correct_amis,
                    'correct_chinese': correct_chinese,
                    'reason': correction_reason,
                    'mood': mood,
                    'context_type': context_type,
                    'difficulty': difficulty
                }
                
                st.session_state.correction_log.append(correction_record)
                
                log_path = 'amis_evolution_log.csv'
                
                if os.path.exists(log_path):
                    existing_df = pd.read_csv(log_path)
                    new_record = pd.DataFrame([correction_record])
                    updated_df = pd.concat([existing_df, new_record], ignore_index=True)
                else:
                    updated_df = pd.DataFrame([correction_record])
                
                updated_df.to_csv(log_path, index=False, encoding='utf-8')
                
                st.success("✅ 修正回報已提交！")
                st.balloons()
            
            else:
                st.error("❌ 請填寫所有必填欄位！")
    
    # ==================== 統計分析模式 ====================
    elif app_mode == "📊 統計分析":
        st.header("📊 統計分析")
        st.markdown("查看修正記錄和語境分析")
        st.markdown("---")
        
        log_path = 'amis_evolution_log.csv'
        
        if os.path.exists(log_path):
            log_df = pd.read_csv(log_path)
            
            st.markdown("### 📈 統計信息")
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("總修正數", len(log_df))
            
            with col2:
                st.metric("最後更新", log_df['timestamp'].iloc[-1][:10] if len(log_df) > 0 else "無")
            
            with col3:
                mood_counts = log_df['mood'].value_counts()
                st.metric("最常見心情", mood_counts.index[0] if len(mood_counts) > 0 else "N/A")
            
            with col4:
                context_counts = log_df['context_type'].value_counts()
                st.metric("最常見情境", context_counts.index[0] if len(context_counts) > 0 else "N/A")
            
            st.markdown("---")
            
            st.markdown("### 💭 語境分析")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("**心情/語氣分布**")
                mood_dist = log_df['mood'].value_counts()
                st.bar_chart(mood_dist)
            
            with col2:
                st.markdown("**使用情境分布**")
                context_dist = log_df['context_type'].value_counts()
                st.bar_chart(context_dist)
            
            with col3:
                st.markdown("**難度等級分布**")
                difficulty_dist = log_df['difficulty'].value_counts()
                st.bar_chart(difficulty_dist)
            
            st.markdown("---")
            
            st.markdown("### 📋 修正記錄詳情")
            
            for idx, row in log_df.iterrows():
                with st.expander(f"修正 #{idx+1} - {row['timestamp'][:10]}"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**❌ 錯誤的句子**")
                        st.write(f"族語：{row['error_amis']}")
                        st.write(f"中文：{row['error_chinese']}")
                    
                    with col2:
                        st.markdown("**✅ 正確的句子**")
                        st.write(f"族語：{row['correct_amis']}")
                        st.write(f"中文：{row['correct_chinese']}")
                    
                    st.markdown("---")
                    
                    st.markdown("**💭 語境備註**")
                    st.write(f"心情/語氣：{row['mood']}")
                    st.write(f"使用情境：{row['context_type']}")
                    st.write(f"難度等級：{row['difficulty']}")
                    
                    st.markdown("**📝 修正說明**")
                    st.write(row['reason'])
            
            st.markdown("---")
            
            st.markdown("### 📥 導出數據")
            
            csv = log_df.to_csv(index=False, encoding='utf-8')
            st.download_button(
                label="📥 下載修正記錄（CSV）",
                data=csv,
                file_name=f"amis_correction_log_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        else:
            st.info("📭 還沒有修正記錄。開始提交修正吧！")

# 頁腳
st.markdown("---")
st.markdown("""
    <div style="text-align: center; color: #7f8c8d; font-size: 0.9rem;">
    <p>🗣️ 族語 Siri - 角色化版 | 基於 Streamlit 開發</p>
    <p>✨ 功能：角色選擇 | 人格化回覆 | ElevenLabs 語音合成</p>
    <p>角色：Pulaw (👨 男聲) | Panay (👩 女聲)</p>
    </div>
""", unsafe_allow_html=True)
