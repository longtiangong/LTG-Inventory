from datetime import datetime
import os
import pandas as pd
import streamlit as st

# 設定網頁標題
st.set_page_config(
    page_title="宮廟庫存管理系統", page_icon="⛩️", layout="wide"
)

# 資料儲存檔案
DATA_FILE = "temple_inventory.csv"

# 初始化資料結構
def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        # 建立預設範例資料（對應您提供的欄位）
        df = pd.DataFrame(
            columns=[
                "項目",
                "進貨日期",
                "進貨數量",
                "使用日期",
                "使用項目",
                "使用數量",
                "盤點日期",
                "盤點數量",
                "結果",
                "補貨日期",
                "補貨數量",
                "總庫存量",
                "供應商名稱",
                "電話",
                "聯絡人",
            ]
        )
        # 載入您的範例資料
        sample_data = {
            "項目": "壽麵",
            "進貨日期": "20260816",
            "進貨數量": 100,
            "使用日期": "20260930",
            "使用項目": "九月聖誕",
            "使用數量": 80,
            "盤點日期": "20261019",
            "盤點數量": 20,
            "結果": "相符",
            "補貨日期": "20261021",
            "補貨數量": 100,
            "總庫存量": 120,
            "供應商名稱": "龍口麵",
            "電話": "0910143517",
            "聯絡人": "張智順",
        }
        df = pd.concat([df, pd.DataFrame([sample_data])], ignore_index=True)
        df.to_csv(DATA_FILE, index=False)
        return df


df = load_data()

st.title("⛩️ 宮廟物資庫存管理系統 {app_version}".format(app_version="v1.0"))
st.markdown("---")

# 安全存量設定
SAFETY_STOCK = 100

# ----------------- 警報檢查區 -----------------
alerts = []
for index, row in df.iterrows():
    item_name = row["項目"]
    total_stock = int(row["總庫存量"])
    check_stock = int(row["盤點數量"])

    if total_stock < SAFETY_STOCK:
        alerts.append(f"【{item_name}】總庫存量 ({total_stock}包) 小於安全數量 {SAFETY_STOCK} 包！")
    if check_stock < SAFETY_STOCK:
        alerts.append(
            f"【{item_name}】盤點數量 ({check_stock}包) 小於安全數量 {SAFETY_STOCK} 包！"
        )

if alerts:
    st.error("🚨 庫存短缺警報：")
    for alert in alerts:
        st.markdown(
            f'<p style="color:red; font-weight:bold; font-size:18px;">{alert}</p>',
            unsafe_allow_html=True,
        )

    # 語音警報 (使用瀏覽器內建語音合成)
    alert_text = "警告！" + "，".join(alerts)
    js_code = f"""
    <script>
        const speech = new SpeechSynthesisUtterance("{alert_text}");
        speech.lang = 'zh-TW';
        window.speechSynthesis.speak(speech);
    </script>
    """
    st.components.v1.html(js_code, height=0)

# ----------------- 密碼權限控制 -----------------
st.sidebar.header("🔐 系統管理登入")
password = st.sidebar.text_input("請輸入管理密碼才能進行增修", type="password")
#提示密碼設定為 ltg6399 (您可自行修改)
AUTH_PASSWORD = "ltg6399"

is_authenticated = password == AUTH_PASSWORD

if not password:
    st.sidebar.info("提示：預設登入密碼為 `ltg+生日`")
elif not is_authenticated:
    st.sidebar.error("密碼錯誤，無法進行新增與修改！")

# ----------------- 主畫面：現有庫存總覽 -----------------
st.subheader("📦 目前庫存總覽表")
st.dataframe(df, use_container_width=True)

# ----------------- 增修管理區 (需密碼) -----------------
st.markdown("---")
st.subheader("📝 庫存資料增修作業")

if is_authenticated:
    st.success("✅ 密碼驗證成功，您可以進行新增或修改。")

    with st.form("inventory_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            item = st.selectbox(
                "1. 項目",
                [
                    "壽麵",
                    "香品",
                    "金紙",
                    "平安符",
                    "光明燈油",
                    "其他 (自行輸入)",
                ],
            )
            if item == "其他 (自行輸入)":
                item = st.text_input("輸入自訂項目名稱")

            restock_date1 = st.text_input("2. 進貨日期 (例: 20260816)", "20260816")
            restock_qty1 = st.number_input("3. 進貨數量", value=100)
            use_date = st.text_input("4. 使用日期 (例: 20260930)", "20260930")
            use_item = st.text_input("5. 使用項目", "九月聖誕")

        with col2:
            use_qty = st.number_input("6. 使用數量", value=80)
            check_date = st.text_input("7. 盤點日期 (例: 20261019)", "20261019")
            check_qty = st.number_input("8. 盤點數量", value=20)

            # 自動計算結果 (盤盈/盤虧/相符)
            calculated_stock = restock_qty1 - use_qty
            if check_qty > calculated_stock:
                result_status = "盤盈"
            elif check_qty < calculated_stock:
                result_status = "盤虧"
            else:
                result_status = "相符"

            st.text(f"9. 結果自動判定：{result_status}")

            restock_date2 = st.text_input("10. 補貨日期 (例: 20261021)", "20261021")

        with col3:
            restock_qty2 = st.number_input("11. 補貨數量", value=100)

            # 自動計算總庫存量 = 盤點數量 + 第二次補貨數量
            total_inventory = check_qty + restock_qty2
            st.metric(label="12. 總庫存量 (自動計算)", value=total_inventory)

            supplier = st.text_input("13. 供應商名稱", "龍口麵")
            phone = st.text_input("14. 電話", "0910143517")
            contact = st.text_input("15. 聯絡人", "張智順")

        submitted = st.form_submit_button("儲存 / 更新庫存資料")

        if submitted:
            new_row = {
                "項目": item,
                "進貨日期": restock_date1,
                "進貨數量": restock_qty1,
                "使用日期": use_date,
                "使用項目": use_item,
                "使用數量": use_qty,
                "盤點日期": check_date,
                "盤點數量": check_qty,
                "結果": result_status,
                "補貨日期": restock_date2,
                "補貨數量": restock_qty2,
                "總庫存量": total_inventory,
                "供應商名稱": supplier,
                "電話": phone,
                "聯絡人": contact,
            }

            # 【修正處】：若該項目已存在，先過濾掉舊的，再與新資料合併，避開型態錯誤
            if item in df["項目"].values:
                df = df[df["項目"] != item]

            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

            df.to_csv(DATA_FILE, index=False)
            st.success(f"【{item}】資料已成功更新！")
            st.rerun()
else:
    st.warning("🔒 請先於左側側邊欄輸入正確密碼，解鎖後即可編輯表單。")