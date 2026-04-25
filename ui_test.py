import streamlit as st

st.title("Instagram Followers Updater")
st.write("Clean UI test is working.")

sheet_url = st.text_input("Paste Google Sheet URL")
worksheet_name = st.text_input("Worksheet name", value="Sheet1")

if st.button("Update Followers"):
    st.success("Button working. Next we connect the real bot.")
    st.write("Sheet URL:", sheet_url)
    st.write("Worksheet:", worksheet_name)
