import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import re
import easyocr
import numpy as np
from PIL import Image

st.set_page_config(page_title="Ramadan Ayomide", layout="wide")

st.title("📚 Ramadan Ayomide - Ultimate AI Author Email Finder")
st.write("Upload a book cover photo or enter an author name to instantly extract emails via local AI scanning.")

# Initialize the local AI Reader (cached so it only loads once)
@st.cache_resource
def load_ocr_reader():
    return easyocr.Reader(['en'], gpu=False)

reader = load_ocr_reader()

def deep_search_author(search_term):
    if not search_term or len(search_term.strip()) < 3:
        return "Invalid Input", "Search query too short."
    try:
        query = f'"{search_term.strip()}" author email contact'
        url = f"https://google.com{query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            text_pool = soup.get_text()
            
            email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
            emails = set(re.findall(email_pattern, text_pool))
            clean_emails = [e for e in emails if not e.endswith(('.png', '.jpg', '.jpeg', '.gif', '.css', '.js'))]
            
            if clean_emails:
                return "AI Local Core Search", ", ".join(clean_emails)
                
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if "url?q=" in href and "google.com" not in href:
                    clean_url = href.split("url?q=")[1].split("&")[0]
                    return clean_url, "Direct email hidden. Link provided for manual contact form."
    except:
        pass
    return "Global Match", f"No public email found for '{search_term}'. Check manual records."

if 'results' not in st.session_state:
    st.session_state.results = []

# --- FEATURE: BOOK COVER IMAGE UPLOADER ---
st.subheader("📸 Option 1: Upload Book Cover Screenshot")
uploaded_file = st.file_uploader("Drag and drop or browse a book cover image:", type=["jpg", "jpeg", "png"])

if uploaded_file is not None:
    st.image(uploaded_file, caption="Uploaded Book Cover", width=200)
    
    if st.button("🤖 Analyze Cover with AI"):
        with st.spinner("AI engine is scanning image pixels directly..."):
            try:
                # Convert the uploaded image file to an array the local AI can read
                image = Image.open(uploaded_file)
                img_array = np.array(image)
                
                # Run local pixel scanning
                ocr_results = reader.readtext(img_array, detail=0)
                
                # Filter out numbers/short gibberish, keep words that look like titles/names
                valid_words = [word.strip() for word in ocr_results if len(word.strip()) > 3 and not word.strip().isdigit()]
                
                if valid_words:
                    # Join detected strings into a combined search phrase
                    detected_text = " ".join(valid_words[:4]) 
                    st.success(f"🔍 AI Successfully Read Text from Cover: **{detected_text}**")
                    
                    source, email = deep_search_author(detected_text)
                    st.session_state.results.append({
                        "Author/Book Name": detected_text,
                        "Official Source": source,
                        "Email Address": email
                    })
                else:
                    st.error("AI scanned the image but couldn't find distinct letters. Try typing it manually below.")
            except Exception as e:
                st.error("AI scanning error. Please use the manual text box below.")

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
    
