import streamlit as st

from navigation import PAGE_ROUTES

pages = [
    st.Page(path, title=title, url_path=url, default=index == 0)
    for index, (path, title, url) in enumerate(PAGE_ROUTES)
]
st.navigation(pages, position="hidden").run()
