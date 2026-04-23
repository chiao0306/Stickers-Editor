import streamlit as st
import streamlit.components.v1 as components
from streamlit_cropper import st_cropper
from PIL import Image
from rembg import remove, new_session
import io
import zipfile

# --- 1. 網頁基礎設定 ---
st.set_page_config(page_title="貼圖去背助手 - 專業版", layout="centered")

# --- 2. 側邊欄設定區 (Sidebar) ---
st.sidebar.header("🛠️ AI 去背設定")

# 模型選擇
model_option = st.sidebar.selectbox(
    "選擇 AI 模型",
    ["u2net (通用)", "isnet-general-use (推薦插畫)", "u2netp (快速輕量)"],
    index=1,
    help="isnet 對於文字和插畫的判定通常比較精準。"
)

# 進階去背設定 (Alpha Matting)
st.sidebar.markdown("---")
use_matting = st.sidebar.checkbox("開啟進階邊緣保留 (Matting)", value=True, help="防止身體或文字被誤砍，邊緣更柔和。")

if use_matting:
    fg_threshold = st.sidebar.slider("前景門檻值", 0, 255, 240, help="越高越能保留更多細節，但也可能殘留背景。")
    bg_threshold = st.sidebar.slider("背景門檻值", 0, 255, 10, help="越低越能徹底去除背景。")
    erode_size = st.sidebar.slider("邊緣侵蝕大小", 0, 30, 10, help="調整邊緣平滑的程度。")

st.sidebar.markdown("---")
st.sidebar.write("### 使用說明")
st.sidebar.info("1. 上傳原圖\n2. 調整紅框包含文字與人物\n3. 點擊懸浮按鈕加入暫存\n4. 全部完成後一鍵批次去背")

# --- 3. 終極 JavaScript 注入 (強制懸浮魔法) ---
components.html(
    """
    <script>
    const parentDoc = window.parent.document;
    const applyFloatingStyle = setInterval(() => {
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(b => {
            if (b.innerText.includes('將此圖加入暫存區')) {
                b.style.position = 'fixed';
                b.style.bottom = '40px';
                b.style.left = '50%';
                b.style.transform = 'translateX(-50%)';
                b.style.zIndex = '9999';
                b.style.width = '85%';
                b.style.maxWidth = '350px';
                b.style.height = '60px';
                b.style.borderRadius = '50px';
                b.style.boxShadow = '0px 10px 25px rgba(0, 0, 0, 0.6)';
                b.style.fontSize = '18px';
                b.dataset.floated = "true";
            }
        });
        if (parentDoc.querySelector('button[data-floated="true"]')) {
            clearInterval(applyFloatingStyle);
        }
    }, 200);
    </script>
    """,
    height=0, width=0,
)

# --- 4. 初始化暫存區 ---
if 'staged_crops' not in st.session_state:
    st.session_state.staged_crops = []

st.title("✂️ 貼圖手動框選 + AI 去背")

# --- 5. 圖片上傳區 ---
uploaded_file = st.file_uploader("1. 匯入貼圖原圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    st.write("### 2. 框選你要的物件")
    
    # 互動式裁切框
    cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
    
    # 預覽區
    st.write("**目前框選預覽：**")
    st.image(cropped_img, width=150)
    st.write("<br><br><br>", unsafe_allow_html=True) 

    # 加入暫存區按鈕
    if st.button("➕ 將此圖加入暫存區", type="primary", use_container_width=True):
        st.session_state.staged_crops.append(cropped_img)
        st.rerun()

st.divider()

# --- 6. 暫存區與一鍵批次處理 ---
if st.session_state.staged_crops:
    st.write(f"### 3. 您的暫存區 (共 {len(st.session_state.staged_crops)} 張)")
    cols = st.columns(3)
    for i, crop in enumerate(st.session_state.staged_crops):
        with cols[i % 3]:
            st.image(crop, caption=f"圖 {i+1}", use_column_width=True)
            
    if st.button("🗑️ 清空暫存區", type="secondary"):
        st.session_state.staged_crops = []
        st.rerun()

    st.write("### 4. AI 魔法時間")
    if st.button("✨ 一鍵批次去背並下載", type="primary", use_container_width=True):
        with st.spinner(f"正在下載/讀取 {model_option} 模型，請稍候..."):
            
            # 根據側邊欄選擇建立 AI Session
            model_name = model_option.split(" ")[0]
            my_session = new_session(model_name)
            
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                for idx, crop in enumerate(st.session_state.staged_crops):
                    
                    # 判斷是否使用 Matting 參數
                    if use_matting:
                        output_img = remove(
                            crop, 
                            session=my_session,
                            alpha_matting=True,
                            alpha_matting_foreground_threshold=fg_threshold,
                            alpha_matting_background_threshold=bg_threshold,
                            alpha_matting_erode_size=erode_size
                        )
                    else:
                        output_img = remove(crop, session=my_session)
                    
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
