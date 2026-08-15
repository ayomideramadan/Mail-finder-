import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Ramadan Ayomide", layout="wide")

st.title("📚 Ramadan Ayomide - Author Email Finder")
st.write("Find author email addresses automatically by searching their official websites.")

def find_author_website(author_name):
    try:
        query = f"{author_name} official website contact"
        url = f"https://google.com{query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if "url?q=" in href and "google.com" not in href:
                    clean_url = href.split("url?q=")[1].split("&")[0]
                    return clean_url
    except:
        pass
    return None

def extract_emails(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=10)
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        emails = set(re.findall(email_pattern, response.text))
        clean_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
        return clean_emails if clean_emails else ["No direct email found. Check page manually."]
    except:
        return ["No direct email found. Check page manually."]

# Initialize session state for results
if 'results' not in st.session_state:
    st.session_state.results = []

# Single search interface
author_input = st.text_input("Enter Author Name or Book Title:")
if st.button("Search"):
    if author_input:
        with st.spinner(f"Searching for {author_input}..."):
            site = find_author_website(author_input)
            if site:
                emails = extract_emails(site)
                for email in emails:
                    st.session_state.results.append({
                        "Author/Book Name": author_input,
                        "Official Website": site,
                        "Email Address": email
                    })
            else:
                st.session_state.results.append({
                    "Author/Book Name": author_input,
                    "Official Website": "Not Found",
                    "Email Address": "Could not locate website"
                })

# Display Results Table
if st.session_state.results:
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True)
    
    # Download Button
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Results as CSV", csv, "author_emails.csv", "text/csv")
    
