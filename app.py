import pandas as pd
import streamlit as st
from io import BytesIO

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="Primavera XER Merge Tool",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Primavera XER Merge Tool")
st.write(
    "Upload a Primavera XER file and an Excel file. "
    "The tool will extract the TASK table from the XER, "
    "merge on task_code, and generate the output Excel file."
)

# --------------------------------------------------
# Read TASK table from XER
# --------------------------------------------------

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


# --------------------------------------------------
# File Upload
# --------------------------------------------------

xer_file = st.file_uploader(
    "Upload Primavera XER File",
    type=["xer"]
)

excel_file = st.file_uploader(
    "Upload Excel File",
    type=["xlsx", "xls"]
)

# --------------------------------------------------
# Merge Process
# --------------------------------------------------

if st.button("Merge Files"):

    if xer_file is None:
        st.error("Please upload the XER file.")
        st.stop()

    if excel_file is None:
        st.error("Please upload the Excel file.")
        st.stop()

    try:

        # Read XER TASK table
        df_a = read_xer_task_table(xer_file)

        # Read Excel file
        df_b = pd.read_excel(excel_file)

        # Clean column names
        df_b.columns = (
            df_b.columns
            .str.strip()
            .str.lower()
        )

        # Remove duplicate task codes
        df_a = df_a.drop_duplicates(subset=["task_code"])
        df_b = df_b.drop_duplicates(subset=["task_code"])

        # Required XER columns
        xer_columns = [
            "task_code",
            "proj_id",
            "task_id",
            "phys_complete_pct"
        ]

        missing_cols = [
            col for col in xer_columns
            if col not in df_a.columns
        ]

        if missing_cols:
            st.error(
                f"Missing columns in TASK table: {missing_cols}"
            )
            st.stop()

        # Merge
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

        # Required Output Columns
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
            "base_end_date",
            "base_start_date",
            "actv_code_scope_for_s_curve_id",
            "phys_complete_pct"
        ]

        # Create blank columns if missing
        for col in output_columns:
            if col not in merged_df.columns:
                merged_df[col] = ""

        result_df = merged_df[output_columns]

        # Statistics
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

        # Create Excel output in memory
        output = BytesIO()

        with pd.ExcelWriter(
            output,
            engine="openpyxl"
        ) as writer:

            result_df.to_excel(
                writer,
                index=False,
                sheet_name="Merged Output"
            )

        output.seek(0)

        st.download_button(
            label="📥 Download Output File",
            data=output,
            file_name="Merged_Output.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error(f"Error: {str(e)}")
