from __future__ import annotations

import json

import pandas as pd
import streamlit as st
from PIL import Image


# Load JSON
@st.cache_data
def load_data(json_file):
    data = json.load(json_file)
    df = pd.DataFrame.from_dict(data, orient="index")
    df = df.sort_values("image_basename")
    return df


st.title("Dynamic Image Filter")
# Set env keys
st_env_keys = [
    "tmp_file",
    "tmp_file_counter",
]
for env in st_env_keys:
    if env not in st.session_state:
        st.session_state[env] = 0
selected_col = "selected_images"
if selected_col not in st.session_state:
    st.session_state[selected_col] = set()

json_file = st.file_uploader("Upload JSON file", type="json")
if json_file is not None:
    if not st.session_state.tmp_file:
        df = load_data(json_file)
    else:
        with open(st.session_state.tmp_file) as file:
            df = load_data(file)
    # --- Filters Section ---
    st.sidebar.header("Build Filters")
    st.sidebar.write("Choose filters and combine with AND/OR")

    filters = []
    num_filters = st.sidebar.number_input("Number of filters", 1, 10, 1)

    for i in range(num_filters):
        st.sidebar.markdown(f"### Filter {i+1}")
        col = st.sidebar.selectbox(
            f"Attribute {i+1}",
            options=df.columns,
            key=f"col_{i}_{st.session_state.tmp_file_counter}",
        )
        operator = st.sidebar.selectbox(
            f"Operator {i+1}",
            options=["AND", "OR"],
            key=f"op_{i}_{st.session_state.tmp_file_counter}",
        )

        # Filter UI
        if df[col].dtype == "bool":
            val = st.sidebar.radio(
                f"Value for {col}",
                options=[True, False],
                key=f"val_{i}_{st.session_state.tmp_file_counter}",
            )
            filters.append((col, val, operator))
        elif pd.api.types.is_numeric_dtype(df[col]):
            min_val, max_val = float(df[col].min()), float(df[col].max())
            min_input = st.sidebar.number_input(
                f"Min {col}",
                value=min_val,
                format="%.6f",
                key=f"min_{i}_{col}_{st.session_state.tmp_file_counter}",
            )
            max_input = st.sidebar.number_input(
                f"Max {col}",
                value=max_val,
                format="%.6f",
                key=f"max_{i}_{col}_{st.session_state.tmp_file_counter}",
            )
            filters.append((col, (min_input, max_input), operator))
        else:
            val = st.sidebar.text_input(
                f"Exact match for {col}",
                key=f"val_{i}_{st.session_state.tmp_file_counter}",
            )
            if val.strip():
                filters.append((col, val, operator))

    mask = pd.Series([False] * len(df), index=df.index)
    for i, (col, val, op) in enumerate(filters):
        if isinstance(val, tuple):  # numeric range
            condition = (df[col] >= val[0]) & (df[col] <= val[1])
        else:
            condition = df[col] == val
        if i == 0:
            mask = condition
        else:
            mask = mask & condition if op == "AND" else mask | condition

    mask = mask & (~df["image_basename"].isin(set(st.session_state.selected_images)))

    filtered_df = df[mask]
    st.write(f"Found {len(filtered_df)} matching images")
    image_options = df["image_basename"].sort_values()
    st.multiselect(
        "Remove Individual Images",
        options=image_options,
        key="selected_images",
    )

    # --- Right-side Pagination Controls ---
    st.markdown("---")
    col1, col2 = st.columns([3, 1])  # main content / right controls

    with col2:
        page_size = st.number_input("Images per page", 1, 50, 12)
        total_pages = max(1, (len(filtered_df) + page_size - 1) // page_size)
        page = st.number_input("Page", 1, total_pages, 1)
        selection_cols = st.columns(2)
        filter_selection = selection_cols[0].button(
            "Set Selection",
            type="primary",
            use_container_width=True,
        )
        remove_selection = selection_cols[1].button(
            "Remove Selection",
            type="primary",
            use_container_width=True,
        )
        if remove_selection or filter_selection:
            filename = "data/tmp_file.json"
            data_dump = df[~mask] if remove_selection else filtered_df
            with open(filename, "w") as file:
                file.write(json.dumps(data_dump.to_dict(orient="index"), indent=2))
            st.session_state.tmp_file = filename
            st.session_state.tmp_file_counter += 1
            load_data.clear()
            st.rerun()
        download_cols = st.columns(2)
        download_cols[0].download_button(
            label="Download Selection",
            data=json.dumps(filtered_df.to_dict(orient="index"), indent=2).encode(
                "utf-8",
            ),
            file_name="filtered-images.json",
            mime="application/json",
            use_container_width=True,
        )
        download_cols[1].download_button(
            label="Download Remainder",
            data=json.dumps(df[~mask].to_dict(orient="index"), indent=2).encode(
                "utf-8",
            ),
            file_name="filtered-images.json",
            mime="application/json",
            use_container_width=True,
        )

    # Slice for current page
    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    page_df = filtered_df.iloc[start_idx:end_idx]

    # --- Display Images ---
    with col1:
        st.write(f"Page {page} of {total_pages}")
        cols_per_row = 4
        cols = st.columns(cols_per_row)
        for idx, row in enumerate(page_df.iterrows()):
            col = cols[idx % cols_per_row]
            with col:
                st.image(
                    Image.open(row[1]["image_path"]),
                    caption=row[1]["image_basename"],
                    width=200,
                )
                with st.expander("Attributes"):
                    st.json(row[1].to_dict())
