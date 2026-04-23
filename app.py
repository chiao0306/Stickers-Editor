import streamlit as st
import streamlit.components.v1 as components
from streamlit_cropper import st_cropper
from PIL import Image
from rembg import remove
import io
import zipfile

# --- 網頁基礎設定 ---
st.set_page_config(page_title="手動框選 + AI 去背神器", layout="centered")

# --- 終極 JavaScript 注入 (強制懸浮魔法) ---
# 因為許多手機瀏覽器不支援最新的 CSS，我們直接用 JS 暴力修改按鈕樣式
components.html(
    """
    <script>
    const parentDoc = window.parent.document;
    
    // 建立一個循環偵測，因為 Streamlit 渲染畫面需要一點時間
    const applyFloatingStyle = setInterval(() => {
        const buttons = parentDoc.querySelectorAll('button');
        buttons.forEach(b => {
            // 透過按鈕上面的文字精準鎖定它
            if (b.innerText.includes('將此圖加入暫存區')) {
                // 找到了！強制覆蓋 CSS 讓它飛起來
                b.style.position = 'fixed';
                b.style.bottom = '40px';
                b.style.left = '50%';
                b.style.transform = 'translateX(-50%)';
                b.style.zIndex = '9999';
                
                // 膠囊形狀與立體質感美化
                b.style.width = '85%';
                b.style.maxWidth = '350px';
                b.style.height = '60px';
                b.style.borderRadius = '50px';
                b.style.boxShadow = '0px 10px 25px rgba(0, 0, 0, 0.6)';
                b.style.border = '2px solid rgba(255, 255, 255, 0.2)';
                b.style.fontSize = '18px';
                
                // 為了避免重複執行，加個標記
                b.dataset.floated = "true";
            }
        });
        
        // 只要找到並設定好，就可以停止偵測了
        if (parentDoc.querySelector('button[data-floated="true"]')) {
            clearInterval(applyFloatingStyle);
        }
    }, 200);
    </script>
    """,
    height=0,
    width=0,
)

# --- 初始化暫存區 (Session State) ---
if 'staged_crops' not in st.session_state:
    st.session_state.staged_crops = []

st.title("✂️ 貼圖手動框選 + AI 去背")

# --- 1. 圖片上傳區 ---
uploaded_file = st.file_uploader("1. 匯入貼圖原圖", type=["png", "jpg", "jpeg"])

if uploaded_file is not None:
    img = Image.open(uploaded_file)
    
    st.write("### 2. 框選你要的物件")
    st.info("💡 拖曳紅框包含文字與人物，確認沒問題後點擊畫面下方的懸浮按鈕。")
    
    # 互動式裁切框
    cropped_img = st_cropper(img, realtime_update=True, box_color='#FF0000', aspect_ratio=None)
    
    # 預覽區 (放在上方方便對照)
    st.write("**目前框選預覽：**")
    st.image(cropped_img, width=150)

    # 墊一點空白，避免滑到最底時被漂浮按鈕擋住圖片底部
    st.write("<br><br><br>", unsafe_allow_html=True) 
    
    # 這個按鈕現在會被我們最上面的 JavaScript 強制抓走變成漂浮狀態
    if st.button("➕ 將此圖加入暫存區", type="primary", use_container_width=True):
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
