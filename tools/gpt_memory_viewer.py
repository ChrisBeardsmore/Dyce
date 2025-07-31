import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
from sqlite_test_patch import get_connection, get_memory, log_gpt_note

st.set_page_config(page_title="GPT Memory Viewer", layout="centered")
st.title("🧠 GPT Memory Log")

# Sidebar app selector
apps = ["contract", "gas", "power", "directgas", "directpower", "tools"]
selected_app = st.sidebar.selectbox("Select App", apps)

# Show logs for selected app
conn = get_connection()
logs = get_memory(conn, app=selected_app)

st.subheader(f"Logs for: `{selected_app}`")
if logs:
    for _, _, timestamp, user, message in logs:
        st.markdown(f"**{timestamp}** — *{user}*  \n{message}")
else:
    st.info("No logs found for this app.")

st.markdown("---")

# Add new memory log
with st.form("log_form"):
    new_message = st.text_area("Add a memory note", height=100)
    submitted = st.form_submit_button("Log it")
    if submitted and new_message.strip():
        log_gpt_note(app=selected_app, message=new_message.strip())
        st.success("✅ Note logged. Refresh the page to see it.")
