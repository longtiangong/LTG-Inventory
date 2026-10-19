from datetime import datetime
import json
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
INTEGER_PATTERN = re.compile(r"^[0-9]+$")
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


def latest_item_record(item_rows):
    if item_rows.empty:
        return None
    purchase_dates = pd.to_datetime(
        item_rows["進貨日期"].astype("string"),
        format="%Y%m%d",
        errors="coerce",
    )
    dated_rows = item_rows.loc[purchase_dates.notna()]
    if dated_rows.empty:
        return item_rows.iloc[-1]
    return dated_rows.loc[purchase_dates.loc[dated_rows.index].idxmax()]


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

    return pd.DataFrame(columns=INVENTORY_COLUMNS)


df = load_data()

st.title("⛩️ 宮廟物資庫存管理系統 {app_version}".format(app_version="v1.0"))
st.markdown("---")

# ----------------- 警報檢查區 -----------------
SAFETY_STOCK = 100
alerts = []
for _, row in df.iterrows():
    item_name = row["項目"]
    total_stock = pd.to_numeric(row["總庫存量"], errors="coerce")
    check_stock = pd.to_numeric(row["盤點數量"], errors="coerce")

    if pd.notna(total_stock) and total_stock < SAFETY_STOCK:
        alerts.append(
            f"【{item_name}】總庫存量 ({total_stock:g}包) 小於安全數量 {SAFETY_STOCK} 包！"
        )
    if pd.notna(check_stock) and check_stock < SAFETY_STOCK:
        alerts.append(
            f"【{item_name}】盤點數量 ({check_stock:g}包) 小於安全數量 {SAFETY_STOCK} 包！"
        )

if alerts:
    st.error("🚨 庫存短缺警報：")
    for alert in alerts:
        st.markdown(
            f'<p style="color:red; font-weight:bold; font-size:18px;">{alert}</p>',
            unsafe_allow_html=True,
        )

    alert_text = json.dumps("警告！" + "，".join(alerts), ensure_ascii=False)
    js_code = f"""
    <script>
        const speech = new SpeechSynthesisUtterance({alert_text});
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
    overview.style.map(
        lambda status: "color: red; font-weight: bold"
        if status == "待補貨"
        else "",
        subset=["補貨狀態"],
    ),
    use_container_width=True,
    hide_index=True,
)

# ----------------- 增修管理區 (需密碼) -----------------
st.markdown("---")
st.subheader("📝 庫存資料增修作業")

if is_authenticated:
    st.success("✅ 密碼驗證成功，您可以進行新增或修改。")
    if "save_message" in st.session_state:
        st.success(st.session_state.pop("save_message"))
    if st.session_state.pop("clear_inventory_form", False):
        st.session_state["selected_item"] = "請選擇項目"
        st.session_state["last_form_item"] = "請選擇項目"
        for key in (
            "custom_item",
            "previous_month_stock",
            "purchase_date",
            "purchase_qty",
            "use_date",
            "use_item",
            "use_qty",
            "check_date",
            "check_qty",
            "supplier",
            "phone",
            "contact",
        ):
            st.session_state[key] = ""

    item_options = [
        "壽麵",
        "香品",
        "金紙",
        "平安符",
        "光明燈油",
        "其他 (自行輸入)",
    ]
    selected_item = st.selectbox(
        "1. 項目",
        ["請選擇項目", *item_options],
        key="selected_item",
    )
    item = selected_item
    if selected_item == "其他 (自行輸入)":
        item = st.text_input("輸入自訂項目名稱", key="custom_item")

    existing_rows = df[df["項目"] == item]
    existing = latest_item_record(existing_rows)

    if st.session_state.get("last_form_item") != item:
        previous_stock = (
            pd.to_numeric(existing["總庫存量"], errors="coerce")
            if existing is not None
            else None
        )
        if previous_stock is None or pd.isna(previous_stock):
            previous_stock = (
                pd.to_numeric(existing["上一次月份總庫存量"], errors="coerce")
                if existing is not None
                else None
            )
        st.session_state["previous_month_stock"] = (
            str(int(previous_stock))
            if previous_stock is not None and pd.notna(previous_stock)
            else ""
        )
        st.session_state["last_form_item"] = item

    previous_month = (
        format_month(existing["進貨日期"]) if existing is not None else ""
    )

    with st.form("inventory_form"):
        col1, col2, col3 = st.columns(3)

        with col1:
            st.text(f"2. 上一次月份：{previous_month}")
            previous_month_stock_text = st.text_input(
                "3. 上一次月份總庫存量",
                key="previous_month_stock",
            )
            purchase_date = st.text_input(
                "4. 進貨日期（西元年月日，共 8 碼）",
                key="purchase_date",
            )
            purchase_qty_text = st.text_input(
                "5. 進貨數量",
                key="purchase_qty",
            )
            use_date = st.text_input(
                "6. 使用日期（西元年月日，共 8 碼）",
                key="use_date",
            )

        with col2:
            use_item = st.text_input(
                "7. 使用項目",
                key="use_item",
            )
            use_qty_text = st.text_input(
                "8. 使用數量",
                key="use_qty",
            )
            check_date = st.text_input(
                "9. 盤點日期（西元年月日，共 8 碼）",
                key="check_date",
            )
            check_qty_text = st.text_input(
                "10. 盤點數量",
                key="check_qty",
            )

            quantity_values = (
                previous_month_stock_text,
                purchase_qty_text,
                use_qty_text,
                check_qty_text,
            )
            quantities_valid = all(
                INTEGER_PATTERN.fullmatch(value.strip())
                for value in quantity_values
            )
            calculated_stock = (
                int(purchase_qty_text) - int(use_qty_text)
                if quantities_valid
                else None
            )
            if calculated_stock is None:
                result_status = ""
            elif int(check_qty_text) > calculated_stock:
                result_status = "盤盈"
            elif int(check_qty_text) < calculated_stock:
                result_status = "盤虧"
            else:
                result_status = "相符"

            st.text(f"11. 結果自動判定：{result_status or '待輸入數量'}")

        with col3:
            st.metric(
                label="12. 總庫存量（進貨數量－使用數量）",
                value=calculated_stock if calculated_stock is not None else "—",
            )
            supplier = st.text_input(
                "13. 供應商名稱",
                key="supplier",
            )
            phone = st.text_input(
                "14. 電話",
                key="phone",
            )
            contact = st.text_input(
                "15. 聯絡人",
                key="contact",
            )

        submitted = st.form_submit_button("儲存 / 更新庫存資料")

        if submitted:
            previous_month_stock_text = previous_month_stock_text.strip()
            quantity_fields = {
                "上一次月份總庫存量": previous_month_stock_text,
                "進貨數量": purchase_qty_text.strip(),
                "使用數量": use_qty_text.strip(),
                "盤點數量": check_qty_text.strip(),
            }
            invalid_dates = [
                label
                for label, value in (
                    ("進貨日期", purchase_date),
                    ("使用日期", use_date),
                    ("盤點日期", check_date),
                )
                if parse_date(value) is None
            ]
            missing_fields = [
                label
                for label, value in (
                    ("使用項目", use_item),
                    ("供應商名稱", supplier),
                    ("電話", phone),
                    ("聯絡人", contact),
                )
                if not value.strip()
            ]
            if selected_item == "請選擇項目" or not item.strip():
                st.error("請輸入項目名稱。")
            elif any(
                not INTEGER_PATTERN.fullmatch(value)
                for value in quantity_fields.values()
            ):
                st.error("所有數量欄位皆須填寫 0 或正整數，不可留白或包含加減符號。")
            elif missing_fields:
                st.error("以下欄位不可留白：" + "、".join(missing_fields))
            elif invalid_dates:
                st.error(
                    "日期格式錯誤或日期不存在，請輸入 8 碼有效西元日期（YYYYMMDD）："
                    + "、".join(invalid_dates)
                )
            else:
                new_row = {
                    "項目": item,
                    "上一次月份": previous_month,
                    "上一次月份總庫存量": int(previous_month_stock_text),
                    "進貨日期": purchase_date,
                    "進貨數量": int(purchase_qty_text),
                    "使用日期": use_date,
                    "使用項目": use_item,
                    "使用數量": int(use_qty_text),
                    "盤點日期": check_date,
                    "盤點數量": int(check_qty_text),
                    "結果": result_status,
                    "總庫存量": calculated_stock,
                    "供應商名稱": supplier,
                    "電話": phone,
                    "聯絡人": contact,
                }

                updated_df = (
                    df[df["項目"] != item]
                    if item in df["項目"].values
                    else df
                )
                updated_df = pd.concat(
                    [updated_df, pd.DataFrame([new_row])], ignore_index=True
                )[INVENTORY_COLUMNS]
                try:
                    updated_df.to_csv(DATA_FILE, index=False)
                except OSError as error:
                    st.error(f"庫存資料儲存失敗：{error}")
                else:
                    st.session_state["save_message"] = f"【{item}】資料已成功更新！"
                    st.session_state["clear_inventory_form"] = True
                    st.rerun()
else:
    st.warning("🔒 請先於左側側邊欄輸入正確密碼，解鎖後即可編輯表單。")