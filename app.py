import streamlit as st

pages = [
    st.Page('pages/0_Overview.py', title='Live overview', default=True),
    st.Page('pages/1_History.py', title='Road history', url_path='History'),
    st.Page('pages/2_Advanced_Analytics.py', title='Patterns & coverage', url_path='Advanced_Analytics'),
    st.Page('pages/3_Route_Planner.py', title='Corridor explorer', url_path='Route_Planner'),
    st.Page('pages/4_AI_Predictor.py', title='Forecast readiness', url_path='AI_Predictor'),
    st.Page('pages/5_RL_Simulation.py', title='What-if lab', url_path='RL_Simulation'),
    st.Page('pages/6_Live_RL_Tracker.py', title='Data status', url_path='Live_RL_Tracker'),
]
st.navigation(pages, position='hidden').run()
