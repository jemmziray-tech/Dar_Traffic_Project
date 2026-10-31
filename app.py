"""Keep existing Streamlit bookmarks useful after the website migration."""

import streamlit as st

WEBSITE = "https://dar-traffic.justolm128.chatgpt.site/"
LEGACY_ROUTES = (
    "Overview",
    "History",
    "Advanced_Analytics",
    "Route_Planner",
    "AI_Predictor",
    "RL_Simulation",
    "Live_RL_Tracker",
)


def moved():
    st.set_page_config(page_title="Dar Traffic has moved", page_icon="↗", layout="centered")
    st.title("Dar Traffic has moved")
    st.write(
        "The new website brings together corridor search, travel estimates, "
        "recorded history and data status in one interface."
    )
    st.link_button("Open Dar Traffic", WEBSITE, type="primary", use_container_width=True)
    st.caption("Update your bookmark. Google Cloud continues collecting the traffic observations.")


pages = [st.Page(moved, title="Dar Traffic", default=True)] + [
    st.Page(moved, title="Dar Traffic", url_path=route) for route in LEGACY_ROUTES
]
st.navigation(pages, position="hidden").run()
