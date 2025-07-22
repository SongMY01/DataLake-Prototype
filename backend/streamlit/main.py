import logging
import streamlit as st
import pandas as pd
from pyiceberg.catalog import load_catalog
from pathlib import Path
import os


logger = logging.getLogger(__name__)

MINIO_ENDPOINT = "http://minio:9000"
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"
BUCKET_NAME = "user-events"


BASE_DIR = Path(__file__).resolve().parent.parent  # backend/
WAREHOUSE_META_PATH = BASE_DIR / "db/warehouse"


# 📌 Iceberg 카탈로그 설정
CATALOG_NAME = "user_catalog"
NAMESPACE = "user_events"

logger.info("Ensuring warehouse metadata directory exists at %s", WAREHOUSE_META_PATH)
os.makedirs(WAREHOUSE_META_PATH, exist_ok=True)

# 카탈로그 로드
catalog = load_catalog(
    CATALOG_NAME,
    **{
        "type": "sql",
        "uri": f"sqlite:///{WAREHOUSE_META_PATH}/pyiceberg_catalog.db",
        "warehouse": f"s3://{BUCKET_NAME}",
        "s3.endpoint": MINIO_ENDPOINT,
        "s3.access-key-id": ACCESS_KEY,
        "s3.secret-access-key": SECRET_KEY,
        "s3.region": "us-east-1",
    }
)

# --- Streamlit 앱 시작 ---
st.set_page_config(page_title="User Events Dashboard", layout="wide")

st.title("🎯 User Events Dashboard")

# 테이블 선택
table_choice = st.selectbox("📋 테이블 선택", options=["click_events", "keydown_events"])
TABLE_NAME = f"{NAMESPACE}.{table_choice}"

if st.button("🔄 최신 데이터 불러오기"):
    st.rerun()

# 테이블 로드
try:
    table = catalog.load_table(TABLE_NAME)
    arrow_table = table.scan().to_arrow()
    df = arrow_table.to_pandas()

    if 'timestamp' in df.columns:
        df["timestamp"] = (
            pd.to_datetime(df["timestamp"], unit="ms", utc=True)
            .dt.tz_convert("Asia/Seoul")
        )
        df = df.sort_values("timestamp", ascending=False)

    st.subheader("📋 Raw Data")
    st.dataframe(df, use_container_width=True)

    st.subheader("🕒 Timestamp Distribution")
    if not df.empty:
        df.set_index("timestamp", inplace=True)
        st.line_chart(df.resample("1min").size())
    else:
        st.info("데이터가 없습니다.")

except Exception as e:
    st.error(f"🚨 테이블 로드 실패: {e}")