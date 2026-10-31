from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_existing_streamlit_address_points_to_the_new_website():
    app = AppTest.from_file(str(Path(__file__).resolve().parents[1] / "app.py")).run()
    assert not app.exception
    assert app.title[0].value == "Dar Traffic has moved"
    assert app.get("link_button")[0].proto.url == "https://dartraffic.vercel.app/"
