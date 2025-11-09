import os, requests, streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Cafeteria Menu RAG Assistant", layout="wide")
st.title("🥗 Cafeteria Menu RAG Assistant")

if "history" not in st.session_state:
    st.session_state.history = []

with st.sidebar:
    st.markdown("### Settings")
    api_url = st.text_input("API URL", value=API_URL)
    top_k = st.slider("Top-K", min_value=1, max_value=10, value=5)
    if st.button("Health Check"):
        try:
            r = requests.get(f"{api_url}/health", timeout=10)
            st.json(r.json())
        except Exception as e:
            st.error(f"Health check failed: {e}")

prompt = st.text_input("Ask about menus, allergens, calories, or dietary options")

if st.button("Ask") and prompt.strip():
    try:
        payload = {"question": prompt, "top_k": top_k}
        r = requests.post(f"{api_url}/query", json=payload, timeout=60)
        data = r.json()
        st.session_state.history.append({"q": prompt, "a": data})
    except Exception as e:
        st.error(f"Query failed: {e}")

for turn in st.session_state.history[::-1]:
    st.markdown(f"**You:** {turn['q']}")
    st.write(turn["a"]["answer"])
    with st.expander("Citations"):
        st.json(turn["a"]["citations"])
    st.divider()
