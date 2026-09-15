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
        # ==========================================

        df_a = read_xer_task_table(xer_file)

        df_b = pd.read_excel(excel_file)

        df_b.columns = (
            df_b.columns
            .str.strip()
            .str.lower()
        )

        # ==========================================
        # Remove Duplicates
        # ==========================================

        df_a = df_a.drop_duplicates(subset=["task_code"])
        df_b = df_b.drop_duplicates(subset=["task_code"])

        # ==========================================
        # Validate Required XER Columns
        # ==========================================

        required_xer_cols = [
            "task_code",
            "proj_id",
            "task_id",
            "phys_complete_pct"
        ]

        missing_cols = [
            col
            for col in required_xer_cols
            if col not in df_a.columns
        ]

        if missing_cols:
            st.error(
                f"Missing columns in XER TASK table: {missing_cols}"
            )
            st.stop()

        # ==========================================
        # Merge
        # ==========================================

        merged_df = pd.merge(
            df_b,
            df_a[
                [
                    "task_code",
                    "proj_id",
                    "task_id",
                    "phys_complete_pct"
                ]
            ],
            on="task_code",
            how="left"
        )

        # ==========================================
        # Derived Columns
        # ==========================================

        if "base_end_date" in merged_df.columns:
            merged_df["new_bl_project_end"] = merged_df["base_end_date"]
        else:
            merged_df["new_bl_project_end"] = ""

        if "base_start_date" in merged_df.columns:
            merged_df["new_project_start"] = merged_df["base_start_date"]
        else:
            merged_df["new_project_start"] = ""

        merged_df["last_recalc_date"] = datetime.today()

        # ==========================================
        # Required Output Columns
        # ==========================================

        output_columns = [
            "user_field_352",
            "start_date",
            "end_date",
            "act_end_date",
            "act_start_date",
            "task_code",
            "proj_id",
            "task_id",
            "task_name",
            "base_line_type",
            "base_end_date",
            "project_filter",
            "base_start_date",
            "last_recalc_date",
            "actv_code_scope_for_s_curve_id",
            "user_field_203",
            "new_bl_project_end",
            "sum_base_project_id",
            "new_project_start",
            "phys_complete_pct"
        ]

        # Create missing columns as blank
        for col in output_columns:
            if col not in merged_df.columns:
                merged_df[col] = ""

        result_df = merged_df[output_columns]

        # ==========================================
        # Delete First Data Row
        # ==========================================

        if len(result_df) > 0:
            result_df = result_df.iloc[1:].reset_index(drop=True)

        # ==========================================
        # Format Dates
        # ==========================================

        date_columns = [
            "start_date",
            "end_date",
            "act_end_date",
            "act_start_date",
            "base_end_date",
            "base_start_date",
            "new_bl_project_end",
            "new_project_start",
            "last_recalc_date"
        ]

        for col in date_columns:
            if col in result_df.columns:
                result_df[col] = pd.to_datetime(
                    result_df[col],
                    errors="coerce"
                ).dt.strftime("%d-%m-%Y")

        # ==========================================
        # Statistics
        # ==========================================

        matched = result_df["proj_id"].notna().sum()
        unmatched = result_df["proj_id"].isna().sum()

        st.success("✅ Merge Completed Successfully")

        col1, col2, col3 = st.columns(3)

        col1.metric(
            "Total Records",
            len(result_df)
        )

        col2.metric(
            "Matched",
            matched
        )

        col3.metric(
            "Unmatched",
            unmatched
        )

        st.subheader("Preview")

        st.dataframe(
            result_df.head(20),
            use_container_width=True
        )

        # ==========================================
        # Create Download File
        # ==========================================

        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            result_df.to_excel(
                writer,
                sheet_name="Merged Output",
                index=False
            )

        output.seek(0)

        output_filename = (
            xer_file.name.replace(
                ".xer",
                "_Merged_Output.xlsx"
            )
        )

        st.download_button(
            label="📥 Download Output File",
            data=output,
            file_name=output_filename,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {str(e)}")
