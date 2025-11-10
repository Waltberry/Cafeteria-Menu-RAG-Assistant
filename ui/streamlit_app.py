# ui/streamlit_app.py
import os
import requests
import streamlit as st

DEFAULT_API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Cafeteria Menu RAG Assistant", layout="wide")
st.title("🥗 Cafeteria Menu RAG Assistant")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown("### Settings")
    api_url = st.text_input("API URL", value=DEFAULT_API_URL)
    top_k = st.slider("Top-K", min_value=1, max_value=10, value=5)
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Health Check"):
            try:
                r = requests.get(f"{api_url}/health", timeout=10)
                st.success("Healthy")
                st.json(r.json())
            except Exception as e:
                st.error(f"Health check failed: {e}")
    with col2:
        if st.button("Clear Chat"):
            st.session_state.history = []
            st.experimental_rerun()

# Use a form so pressing Enter also submits
with st.form("ask_form"):
    prompt = st.text_input("Ask about menus, allergens, calories, or dietary options")
    submitted = st.form_submit_button("Ask")
    if submitted and prompt.strip():
        try:
            payload = {"question": prompt, "top_k": top_k}
            r = requests.post(f"{api_url}/query", json=payload, timeout=60)
            data = r.json()
            st.session_state.history.append({"q": prompt, "a": data})
        except Exception as e:
            st.error(f"Query failed: {e}")

# Show newest first
for turn in st.session_state.history[::-1]:
    st.markdown(f"**You:** {turn['q']}")
    a = turn["a"]

    # Show answer plainly
    st.markdown("**Answer:**")
    st.write(a.get("answer", ""))

    # Helpful summary line
    dbg = a.get("debug", {}) or {}
    st.caption(f"hits: {dbg.get('hits', 'n/a')}")

    # Citations
    with st.expander("Citations (raw)"):
        st.json(a.get("citations", []))

    # Entire response for debugging
    with st.expander("Raw response (debug)"):
        st.json(a)
    st.divider()
