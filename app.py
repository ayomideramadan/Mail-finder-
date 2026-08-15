import streamlit as st
import pandas as pd
import requests

st.set_page_config(page_title="Ramadan Ayomide", layout="wide")

st.title("📚 Ramadan Ayomide - Ultimate Author Email Finder")
st.write("Powered by Live Database API Search to locate verified contact details.")

# Setup fields for API keys (The client inputs their own key)
api_key = "744955b23d9bba7603c4bd3fdfbc8885f81ca99f" # Default test key or let user input it

def find_author_via_database(author_name):
    try:
        # Querying a dedicated professional database endpoint instead of raw web scraping
        url = f"https://tomba.io{author_name.replace(' ', '%20')}"
        headers = {"X-Tomba-Key": api_key}
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            if "email" in data and data["email"]:
                return data.get("website", "Database Records"), data.get("email")
    except:
        pass
    return "Not Found", "Could not locate verified email"

if 'results' not in st.session_state:
    st.session_state.results = []

author_input = st.text_input("Enter Author Name or Book Title:")
if st.button("Search Database"):
    if author_input:
        with st.spinner(f"Querying global records for {author_input}..."):
            site, email = find_author_via_database(author_input)
            st.session_state.results.append({
                "Author/Book Name": author_input,
                "Official Source": site,
                "Email Address": email
            })

if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True)
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Results as CSV", csv, "author_emails.csv", "text/csv")
    
