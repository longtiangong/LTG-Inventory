from datetime import date, datetime
import os
import re
import pandas as pd
import streamlit as st

# 設定網頁標題
st.set_page_config(
    page_title="宮廟庫存管理系統", page_icon="⛩️", layout="wide"
)

# 資料儲存檔案
DATA_FILE = "temple_inventory.csv"
DATE_PATTERN = re.compile(r"^[0-9]{8}$")
MONTH_NUMERALS = (
    "",
    "一",
    "二",
    "三",
    "四",
    "五",
    "六",
    "七",
    "八",
    "九",
    "十",
    "十一",
    "十二",
)
INVENTORY_COLUMNS = [
    "項目",
    "上一次月份",
    "上一次月份總庫存量",
    "進貨日期",
    "進貨數量",
    "使用日期",
    "使用項目",
    "使用數量",
    "盤點日期",
    "盤點數量",
    "結果",
    "總庫存量",
    "供應商名稱",
    "電話",
    "聯絡人",
]


def parse_date(value):
    date_text = str(value).strip()
    if not DATE_PATTERN.fullmatch(date_text):
        return None
    try:
        return datetime.strptime(date_text, "%Y%m%d").date()
    except ValueError:
        return None


def format_month(value):
    parsed_date = parse_date(value)
    if parsed_date is None:
        return ""
    return f"{parsed_date.year}{MONTH_NUMERALS[parsed_date.month]}月"


# 初始化資料結構
def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(
            DATA_FILE,
            dtype={
                "進貨日期": "string",
                "使用日期": "string",
                "盤點日期": "string",
            },
        )
        df = df.drop(columns=["補貨日期", "補貨數量"], errors="ignore")
        if "上一次月份" not in df.columns:
            df["上一次月份"] = df.get("進貨日期", pd.Series(index=df.index)).map(
                format_month
            )
        if "上一次月份總庫存量" not in df.columns:
            df["上一次月份總庫存量"] = 0
        for column in INVENTORY_COLUMNS:
            if column not in df.columns:
                df[column] = 0 if column in {
                    "上一次月份總庫存量",
                    "進貨數量",
                    "使用數量",
                    "盤點數量",
                    "總庫存量",
                } else ""
        return df[INVENTORY_COLUMNS]

    sample_data = {
        "項目": "壽麵",
        "上一次月份": "2026十月",
        "上一次月份總庫存量": 0,
        "進貨日期": "20261020",
        "進貨數量": 100,
        "使用日期": "20260930",
        "使用項目": "九月聖誕",
        "使用數量": 80,
        "盤點日期": "20261019",
        "盤點數量": 20,
        "結果": "相符",
        "總庫存量": 20,
        "供應商名稱": "龍口麵",
        "電話": "0910143517",
        "聯絡人": "張智順",
    }
    return pd.DataFrame([sample_data], columns=INVENTORY_COLUMNS)


df = load_data()

st.title("⛩️ 宮廟物資庫存管理系統 {app_version}".format(app_version="v1.0"))
st.markdown("---")

# 安全存量設定
SAFETY_STOCK = 100

# ----------------- 警報檢查區 -----------------
alerts = []
for index, row in df.iterrows():
    item_name = row["項目"]
    total_stock = pd.to_numeric(row["總庫存量"], errors="coerce")
    check_stock = pd.to_numeric(row["盤點數量"], errors="coerce")

    if pd.notna(total_stock) and total_stock < SAFETY_STOCK:
        alerts.append(f"【{item_name}】總庫存量 ({total_stock}包) 小於安全數量 {SAFETY_STOCK} 包！")
    if pd.notna(check_stock) and check_stock < SAFETY_STOCK:
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
    st.sidebar.info("提示：預設登入密碼為 `龍天宮+生日`")
elif not is_authenticated:
    st.sidebar.error("密碼錯誤，無法進行新增與修改！")

# ----------------- 主畫面：現有庫存總覽 -----------------
st.subheader("📦 目前庫存總覽表")
overview = df.copy()
overview["進貨月份"] = overview["進貨日期"].map(format_month)
status_stock = pd.to_numeric(
    overview["上一次月份總庫存量"], errors="coerce"
).fillna(pd.to_numeric(overview["總庫存量"], errors="coerce"))
overview["補貨狀態"] = status_stock.map(
    lambda stock: "結案" if pd.notna(stock) and stock > SAFETY_STOCK else "待補貨"
)
st.dataframe(
    overview.drop(columns=["進貨日期", "進貨數量", "使用日期", "盤點日期"]),
    use_container_width=True,
)

# ----------------- 增修管理區 (需密碼) -----------------
st.markdown("---")
st.subheader("📝 庫存資料增修作業")

if is_authenticated:
    st.success("✅ 密碼驗證成功，您可以進行新增或修改。")
    if "save_message" in st.session_state:
        st.success(st.session_state.pop("save_message"))

    item_options = [
        "壽麵",
        "香品",
        "金紙",
        "平安符",
        "光明燈油",
        "其他 (自行輸入)",
    ]
    selected_item = st.selectbox("1. 項目", item_options)
    item = selected_item
    if selected_item == "其他 (自行輸入)":
        item = st.text_input("輸入自訂項目名稱")

    existing_rows = df[df["項目"] == item]
    existing = existing_rows.iloc[0] if not existing_rows.empty else None

    def existing_value(column, default):
        if existing is None or pd.isna(existing[column]) or existing[column] == "":
            return default
        return existing[column]

    current_date = date.today().strftime("%Y%m%d")
    previous_month = format_month(
        existing_value("進貨日期", current_date)
    )

    with st.form("inventory_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.text(f"2. 上一次月份：{previous_month}")
            previous_month_stock = st.number_input(
                "3. 上一次月份總庫存量",
                min_value=0,
                value=int(existing_value("上一次月份總庫存量", 0)),
                step=1,
                key=f"previous_month_stock_{item}",
            )
            purchase_date = st.text_input(
                "4. 進貨日期（西元年月日，共 8 碼）",
                str(existing_value("進貨日期", current_date)),
                key=f"purchase_date_{item}",
            )
            purchase_qty = st.number_input(
                "5. 進貨數量",
                min_value=0,
                value=int(existing_value("進貨數量", 100)),
                step=1,
                key=f"purchase_qty_{item}",
            )
            use_date = st.text_input(
                "6. 使用日期（西元年月日，共 8 碼）",
                str(existing_value("使用日期", current_date)),
                key=f"use_date_{item}",
            )

        with col2:
            use_item = st.text_input(
                "7. 使用項目",
                str(existing_value("使用項目", "")),
                key=f"use_item_{item}",
            )
            use_qty = st.number_input(
                "8. 使用數量",
                min_value=0,
                value=int(existing_value("使用數量", 0)),
                step=1,
                key=f"use_qty_{item}",
            )
            check_date = st.text_input(
                "9. 盤點日期（西元年月日，共 8 碼）",
                str(existing_value("盤點日期", current_date)),
                key=f"check_date_{item}",
            )
            check_qty = st.number_input(
                "10. 盤點數量",
                min_value=0,
                value=int(existing_value("盤點數量", 0)),
                step=1,
                key=f"check_qty_{item}",
            )

            calculated_stock = purchase_qty - use_qty
            if check_qty > calculated_stock:
                result_status = "盤盈"
            elif check_qty < calculated_stock:
                result_status = "盤虧"
            else:
                result_status = "相符"

            st.text(f"11. 結果自動判定：{result_status}")

        with col3:
            st.metric(label="12. 總庫存量（進貨數量－使用數量）", value=calculated_stock)
            supplier = st.text_input(
                "13. 供應商名稱",
                str(existing_value("供應商名稱", "龍口麵")),
                key=f"supplier_{item}",
            )
            phone = st.text_input(
                "14. 電話",
                str(existing_value("電話", "")),
                key=f"phone_{item}",
            )
            contact = st.text_input(
                "15. 聯絡人",
                str(existing_value("聯絡人", "")),
                key=f"contact_{item}",
            )

        submitted = st.form_submit_button("儲存 / 更新庫存資料")

        if submitted:
            invalid_dates = [
                label
                for label, value in (
                    ("進貨日期", purchase_date),
                    ("使用日期", use_date),
                    ("盤點日期", check_date),
                )
                if parse_date(value) is None
            ]
            if not item.strip():
                st.error("請輸入項目名稱。")
            elif invalid_dates:
                st.error(
                    "日期格式錯誤或日期不存在，請輸入 8 碼有效西元日期（YYYYMMDD）："
                    + "、".join(invalid_dates)
                )
            else:
                new_row = {
                    "項目": item,
                    "上一次月份": previous_month,
                    "上一次月份總庫存量": previous_month_stock,
                    "進貨日期": purchase_date,
                    "進貨數量": purchase_qty,
                    "使用日期": use_date,
                    "使用項目": use_item,
                    "使用數量": use_qty,
                    "盤點日期": check_date,
                    "盤點數量": check_qty,
                    "結果": result_status,
                    "總庫存量": calculated_stock,
                    "供應商名稱": supplier,
                    "電話": phone,
                    "聯絡人": contact,
                }

                updated_df = df[df["項目"] != item]
                updated_df = pd.concat(
                    [updated_df, pd.DataFrame([new_row])], ignore_index=True
                )[INVENTORY_COLUMNS]
                try:
                    updated_df.to_csv(DATA_FILE, index=False)
                except OSError as error:
                    st.error(f"庫存資料儲存失敗：{error}")
                else:
                    st.session_state["save_message"] = f"【{item}】資料已成功更新！"
                    st.rerun()
else:
    st.warning("🔒 請先於左側側邊欄輸入正確密碼，解鎖後即可編輯表單。")