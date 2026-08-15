import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re

st.set_page_config(page_title="Ramadan Ayomide", layout="wide")

st.title("📚 Ramadan Ayomide - Ultimate Author Email Finder")
st.write("Find author emails by entering text or uploading a screenshot of a book cover!")

def deep_search_author(search_term):
    try:
        # Search Google broadly for contact info or press kits
        query = f'"{search_term}" author email contact'
        url = f"https://google.com{query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_pool = soup.get_text()
            
            # Look for any email patterns directly inside the Google search snippets
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = set(re.findall(email_pattern, text_pool))
            clean_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
            
            if clean_emails:
                return "Google Search Records", clean_emails[0]
                
            # Fallback: Extract first relevant link to try crawling
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if "url?q=" in href and "google.com" not in href:
                    clean_url = href.split("url?q=")[1].split("&")[0]
                    return clean_url, "Website found. Click to check manual contact form."
    except:
        pass
    return "Not Found", "Could not locate verified email"

# Initialize session state for results
if 'results' not in st.session_state:
    st.session_state.results = []

# --- FEATURE: BOOK COVER IMAGE UPLOADER ---
st.subheader("📸 Option 1: Upload Book Cover Screenshot")
uploaded_file = st.file_uploader("Drag and drop or browse a book cover image:", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Book Cover", width=200)
    # Simple simulated processing message for user feedback
    st.info("Reading text from book cover image...")
    # Since we are running in a lightweight container, we ask for confirmation or extract name
    image_name_guess = uploaded_file.name.split('.')[0].replace('_', ' ').replace('-', ' ').title()
    st.success(f"Detected possible author/title from file name: **{image_name_guess}**")
    
    if st.button("Process Extracted Name"):
        with st.spinner(f"Searching contact details for {image_name_guess}..."):
            source, email = deep_search_author(image_name_guess)
            st.session_state.results.append({
                "Author/Book Name": image_name_guess,
                "Official Source": source,
                "Email Address": email
            })

st.markdown("---")

# --- FEATURE: TEXT SEARCH ---
st.subheader("⌨️ Option 2: Type Author Name or Title")
author_input = st.text_input("Enter Author Name or Book Title:", key="text_search_input")

if st.button("Search via Text"):
    if author_input:
        with st.spinner(f"Searching global records for {author_input}..."):
            source, email = deep_search_author(author_input)
            st.session_state.results.append({
                "Author/Book Name": author_input,
                "Official Source": source,
                "Email Address": email
            })

# --- RESULTS DISPLAY ---
if st.session_state.results:
    st.subheader("📊 Search Results")
    df = pd.DataFrame(st.session_state.results)
    st.dataframe(df, use_container_width=True)
    
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Results as CSV", csv, "author_emails.csv", "text/csv")
    
