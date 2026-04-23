import streamlit as st
import streamlit.components.v1 as components
from streamlit_cropper import st_cropper
from PIL import Image
from rembg import remove, new_session
import io
import zipfile

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="貼圖去背助手 - 專業版", layout="centered")

# --- 1.2 模型快取魔法 (拯救記憶體崩潰的核心) ---
# 使用 st.cache_resource 保證同一個模型只會被載入記憶體一次
@st.cache_resource(show_spinner="首次載入 AI 模型中...")
def get_rembg_session(model_name):
    return new_session(model_name)

# --- 1.5 狀態初始化與彈出通知 ---
if 'staged_crops' not in st.session_state:
    st.session_state.staged_crops = []
if 'show_toast' not in st.session_state:
    st.session_state.show_toast = False

# 如果剛加入圖片，就在網頁重整後立刻觸發 Toast 小通知
if st.session_state.show_toast:
    st.toast(f"✅ 成功加入！目前暫存區共 {len(st.session_state.staged_crops)} 張圖", icon="🎉")
    st.session_state.show_toast = False

# --- 2. 側邊欄設定區 ---
st.sidebar.header("🛠️ AI 去背設定")
model_option = st.sidebar.selectbox(
    "選擇 AI 模型",
    ["u2net (通用)", "isnet-general-use (推薦插畫)", "u2netp (快速輕量)"],
    index=1,
    help="isnet 對於文字和插畫的判定通常比較精準。"
)
st.sidebar.markdown("---")
use_matting = st.sidebar.checkbox("開啟進階邊緣保留 (Matting)", value=True, help="防止身體或文字被誤砍，邊緣更柔和。")

if use_matting:
    fg_threshold = st.sidebar.slider("前景門檻值", 0, 255, 240, help="越高越能保留更多細節，但也可能殘留背景。")
    bg_threshold = st.sidebar.slider("背景門檻值", 0, 255, 10, help="越低越能徹底去除背景。")
    erode_size = st.sidebar.slider("邊緣侵蝕大小", 0, 30, 10, help="調整邊緣平滑的程度。")

# --- 3. 終極 JavaScript 注入 (加強懸浮 + 修正捲動) ---
components.html(
    """
    <script>
    const parentDoc = window.parent.document;
    
    // 永恆懸浮魔法
    setInterval(() => {
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(b => {
            if (b.innerText.includes('將此圖加入暫存區')) {
                b.style.position = 'fixed';
                b.style.bottom = '30px';
                b.style.left = '45%'; 
                b.style.transform = 'translateX(-50%)';
                b.style.zIndex = '9999';
                b.style.width = '70%'; 
                b.style.maxWidth = '300px';
                b.style.height = '60px';
                b.style.borderRadius = '50px';
                b.style.boxShadow = '0px 10px 25px rgba(0, 0, 0, 0.6)';
                b.style.fontSize = '18px';
                b.style.backgroundColor = '#ff4b4b'; 
                b.style.color = 'white';
            }
        });
    }, 100);

    // 滑動按鈕
    if (!parentDoc.getElementById('custom-scroll-controls')) {
        const scrollDiv = parentDoc.createElement('div');
        scrollDiv.id = 'custom-scroll-controls';
        scrollDiv.style.cssText = "position:fixed; right:15px; bottom:100px; z-index:9999; display:flex; flex-direction:column; gap:15px;";

        const btnStyle = "width: 45px; height: 45px; border-radius: 50%; border: none; background: rgba(255,255,255,0.9); box-shadow: 0 4px 10px rgba(0,0,0,0.3); font-size: 20px; display: flex; align-items: center; justify-content: center; color: #333; cursor: pointer;";

        const scrollToTarget = (targetId) => {
            const target = parentDoc.getElementById(targetId);
            if (target) target.scrollIntoView({behavior: 'smooth', block: 'start'});
        };

        const upBtn = parentDoc.createElement('button');
        upBtn.innerHTML = '⬆️';
        upBtn.style.cssText = btnStyle;
        upBtn.onclick = () => scrollToTarget('crop-area');

        const downBtn = parentDoc.createElement('button');
        downBtn.innerHTML = '⬇️';
        downBtn.style.cssText = btnStyle;
        downBtn.onclick = () => scrollToTarget('preview-area');

        scrollDiv.appendChild(upBtn);
        scrollDiv.appendChild(downBtn);
        parentDoc.body.appendChild(scrollDiv);
    }
    </script>
    """,
    height=0, width=0,
)

st.title("✂️ 貼圖手動框選 + AI 去背")

# --- 4. 圖片上傳區 ---
uploaded_file = st.file_uploader("1. 匯入貼圖原圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    
    st.markdown('<div id="crop-area"></div>', unsafe_allow_html=True)
    st.write("### 2. 框選你要的物件")
    
    cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
    
    st.markdown('<div id="preview-area"></div>', unsafe_allow_html=True)
    
    # 【新增：即時預覽功能區塊】
    col1, col2 = st.columns(2)
    with col1:
        st.write("**目前框選範圍：**")
        st.image(cropped_img, width=150)
    
    with col2:
        st.write("**去背效果預覽：**")
        if st.button("🔍 測試目前去背參數", help="套用左側參數，預覽此單張圖片的去背結果"):
            with st.spinner("AI 運算中..."):
                # 呼叫快取模型，不再重複佔用記憶體
                model_name = model_option.split(" ")[0]
                my_session = get_rembg_session(model_name)
                
                if use_matting:
                    preview_img = remove(
                        cropped_img, session=my_session, alpha_matting=True,
                        alpha_matting_foreground_threshold=fg_threshold,
                        alpha_matting_background_threshold=bg_threshold,
                        alpha_matting_erode_size=erode_size
                    )
                else:
                    preview_img = remove(cropped_img, session=my_session)
                
                st.image(preview_img, width=150)
    
    st.write("<br><br><br>", unsafe_allow_html=True) 

    if st.button("➕ 將此圖加入暫存區", type="primary", use_container_width=True):
        st.session_state.staged_crops.append(cropped_img)
        st.session_state.show_toast = True
        st.rerun()

st.divider()

# --- 5. 暫存區與一鍵批次處理 ---
if st.session_state.staged_crops:
    st.write(f"### 3. 您的暫存區 (共 {len(st.session_state.staged_crops)} 張)")
    
    for i in range(0, len(st.session_state.staged_crops), 3):
        cols = st.columns(3)
        for j in range(3):
            idx = i + j
            if idx < len(st.session_state.staged_crops):
                crop = st.session_state.staged_crops[idx]
                with cols[j]:
                    st.image(crop, caption=f"圖 {idx+1}", use_column_width=True)
                    if st.button("❌ 刪除", key=f"del_{idx}", use_container_width=True):
                        st.session_state.staged_crops.pop(idx)
                        st.rerun()
            
    st.write("<br>", unsafe_allow_html=True)
    if st.button("🗑️ 清空所有暫存", type="secondary"):
        st.session_state.staged_crops = []
        st.rerun()

    st.write("### 4. AI 魔法時間")
    if st.button("✨ 一鍵批次去背並下載", type="primary", use_container_width=True):
        with st.spinner(f"批次處理中..."):
            
            # 同樣呼叫快取模型
            model_name = model_option.split(" ")[0]
            my_session = get_rembg
