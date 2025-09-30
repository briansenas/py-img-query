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
    return df


st.title("Dynamic Image Filter")

json_file = st.file_uploader("Upload JSON file", type="json")
if json_file is not None:
    df = load_data(json_file)

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
            key=f"col_{i}",
        )
        operator = st.sidebar.selectbox(
            f"Operator {i+1}",
            options=["AND", "OR"],
            key=f"op_{i}",
        )

        # Filter UI
        if df[col].dtype == "bool":
            val = st.sidebar.radio(
                f"Value for {col}",
                options=[True, False],
                key=f"val_{i}",
            )
            filters.append((col, val, operator))
        elif pd.api.types.is_numeric_dtype(df[col]):
            min_val, max_val = float(df[col].min()), float(df[col].max())
            min_input = st.sidebar.number_input(
                f"Min {col}",
                value=min_val,
                format="%.6f",
                key=f"min_{i}_{col}",
            )
            max_input = st.sidebar.number_input(
                f"Max {col}",
                value=max_val,
                format="%.6f",
                key=f"max_{i}_{col}",
            )
            filters.append((col, (min_input, max_input), operator))
        else:
            val = st.sidebar.text_input(f"Exact match for {col}", key=f"val_{i}")
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

    filtered_df = df[mask]
    st.write(f"Found {len(filtered_df)} matching images")

    # --- Right-side Pagination Controls ---
    st.markdown("---")
    col1, col2 = st.columns([3, 1])  # main content / right controls

    with col2:
        page_size = st.number_input("Images per page", 1, 50, 12)
        total_pages = max(1, (len(filtered_df) + page_size - 1) // page_size)
        page = st.number_input("Page", 1, total_pages, 1)

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
                st.image(Image.open(row[1]["image_path"]), caption=row[0], width=200)
                with st.expander("Attributes"):
                    st.json(row[1].to_dict())
