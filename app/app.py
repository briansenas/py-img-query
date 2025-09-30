from __future__ import annotations

from pathlib import Path

import streamlit as st

SCRIPT_PATH = Path(__file__).parent.absolute()


def main():
    search_page = st.Page("pages/visualize.py", title="Search Engine", icon="🔍")
    upload_page = st.Page(
        "pages/measure_attributes.py",
        title="Generate Attributes",
        icon=":material/add_circle:",
    )
    pg = st.navigation([search_page, upload_page])
    st.set_page_config(page_icon="🔍", page_title="Image Dataset Utils", layout="wide")
    pg.run()


if __name__ == "__main__":
    main()
