import streamlit as st

from dashboard import overview
from navigation import PAGE_ROUTES

# Streamlit gives the default page the empty path. Register the named overview
# separately so both / and existing /Overview bookmarks remain valid.
pages = [st.Page(overview, title="Live overview", default=True)] + [
    st.Page(path, title=title, url_path=url) for path, title, url in PAGE_ROUTES
]
st.navigation(pages, position="hidden").run()
