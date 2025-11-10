import os, requests, streamlit as st
import pandas as pd

API_URL = os.getenv("API_URL", "http://api:8000")

st.set_page_config(page_title="Cafeteria Menu RAG Assistant", layout="wide")
st.title("🥗 Cafeteria Menu")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown("### Settings")
    api_url = st.text_input("API URL", value=API_URL)
    top_k = st.slider("Top-K", 1, 10, 5)
    if st.button("Health Check"):
        try:
            r = requests.get(f"{api_url}/health", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(f"Health check failed: {e}")

with st.form("ask"):
    prompt = st.text_input("Ask about menus, allergens, calories, or dietary options")
    submitted = st.form_submit_button("Ask")
    if submitted and prompt.strip():
        try:
            payload = {"question": prompt, "top_k": top_k}
            r = requests.post(f"{api_url}/query", json=payload, timeout=60)
            r.raise_for_status()
            data = r.json()
            st.session_state.history.append({"q": prompt, "a": data})
        except Exception as e:
            st.error(f"Query failed: {e}")

for turn in st.session_state.history[::-1]:
    st.markdown(f"**You:** {turn['q']}")
    a = turn["a"]
    st.markdown(a.get("answer",""))
    dbg = a.get("debug", {})
    st.caption(f"hits: {dbg.get('hits','?')}")
    with st.expander("Citations"):
        cits = a.get("citations", [])
        if cits:
            df = pd.DataFrame(cits)[["source","page","chunk_index","score"]]
            st.dataframe(df, use_container_width=True)
        else:
            st.write("No citations returned.")
    st.divider()
