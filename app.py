import pandas as pd
import streamlit as st
from io import BytesIO
from datetime import datetime

# ==================================================
# Page Setup
# ==================================================

st.set_page_config(
    page_title="Primavera XER Merge Tool",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Primavera XER Merge Tool")

# ==================================================
# Read TASK Table from XER
# ==================================================

def read_xer_task_table(uploaded_file):

    task_columns = []
    task_rows = []
    current_table = None

    content = uploaded_file.read().decode(
        "latin-1",
        errors="ignore"
    )

    for line in content.splitlines():

        if line.startswith("%T"):
            parts = line.split("\t")

            if len(parts) > 1:
                current_table = parts[1]

        elif current_table == "TASK" and line.startswith("%F"):
            task_columns = line.split("\t")[1:]

        elif current_table == "TASK" and line.startswith("%R"):
            task_rows.append(line.split("\t")[1:])

    if len(task_rows) == 0:
        raise Exception("TASK table not found in XER file.")

    df = pd.DataFrame(
        task_rows,
        columns=task_columns
    )

    df.columns = (
        df.columns
        .str.strip()
        .str.lower()
    )

    return df

# ==================================================
# File Upload
# ==================================================

xer_file = st.file_uploader(
    "Upload Primavera XER File",
    type=["xer"]
)

excel_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx", "xls"]
)

# ==================================================
# Merge Button
# ==================================================

if st.button("Merge Files"):

    if xer_file is None:
        st.error("Please upload XER file")
        st.stop()

    if excel_file is None:
        st.error("Please upload Excel file")
        st.stop()

    try:

        # ==========================================
        # Read Files
        # =================================
