import streamlit as st
from streamlit_cropper import st_cropper
from PIL import Image
from rembg import remove
import io
import zipfile

# --- 網頁基礎設定 ---
st.set_page_config(page_title="手動框選 + AI 去背神器", layout="centered")

# --- 初始化暫存區 (Session State) ---
if 'staged_crops' not in st.session_state:
    st.session_state.staged_crops = []

st.title("✂️ 貼圖手動框選 + AI 去背")

# --- 1. 圖片上傳區 ---
uploaded_file = st.file_uploader("1. 匯入貼圖原圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    
    st.write("### 2. 框選你要的物件")
    st.info("💡 拖曳紅框包含文字與人物後，點擊下方「加入暫存區」。")
    
    # 互動式裁切框
    cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
    
    # 預覽與加入按鈕
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image(cropped_img, caption="目前框選預覽", use_column_width=True)
    with col2:
        st.write("") # 排版用留白
        st.write("")
        if st.button("➕ 將此圖加入暫存區", use_container_width=True):
            st.session_state.staged_crops.append(cropped_img)
            st.rerun()

st.divider()

# --- 2. 暫存區與一鍵批次處理 ---
if st.session_state.staged_crops:
    st.write(f"### 3. 您的暫存區 (共 {len(st.session_state.staged_crops)} 張)")
    
    # 將暫存區的圖片並排顯示 (每行 3 張適合手機版)
    cols = st.columns(3)
    for i, crop in enumerate(st.session_state.staged_crops):
        with cols[i % 3]:
            st.image(crop, caption=f"圖 {i+1}", use_column_width=True)
            
    if st.button("🗑️ 清空暫存區", type="secondary"):
        st.session_state.staged_crops = []
        st.rerun()

    st.write("### 4. AI 魔法時間")
    if st.button("✨ 一鍵批次去背並下載", type="primary", use_container_width=True):
        with st.spinner("AI 處理中... (若為首次執行需下載模型，請稍候約 1-2 分鐘)"):
            
            # 在記憶體中準備 ZIP 檔
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, crop in enumerate(st.session_state.staged_crops):
                    # 呼叫 rembg 去背
                    output_img = remove(crop)
                    
                    # 轉成 Byte 塞進 ZIP
                    img_byte_arr = io.BytesIO()
                    output_img.save(img_byte_arr, format='PNG')
                    zip_file.writestr(f"sticker_{idx+1:02d}.png", img_byte_arr.getvalue())
            
            st.success("✅ 全數去背完成！")
            st.download_button(
                label="📥 下載透明貼圖包 (ZIP)",
                data=zip_buffer.getvalue(),
                file_name="smart_stickers.zip",
                mime="application/zip",
                use_container_width=True
            )
