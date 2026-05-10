import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from streamlit_option_menu import option_menu
from PIL import Image
import io
import time

# --- CONFIGURATION ---
st.set_page_config(page_title="DS Academy AI", layout="wide", page_icon="🧪")

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- UTILITY FUNCTIONS ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            text += page.extract_text() or ""
    return text

def split_text(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=7000, chunk_overlap=700)
    return text_splitter.split_text(text)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧪 DS Control Center")
    api_key = st.text_input("Enter Google API Key:", type="password")
    
    st.write("---")
    mode = option_menu(
        menu_title="ft Akademik",
        options=[
            "General Chat", 
            "PDF Analysis", 
            "Presentation Designer", 
            "Data & Graph Insight", 
            "Video Mentor", 
            "Image insight",
            "Video Translate",
            "Audio Insights",
            "Quiz Generator"
        ],
        icons=["chat-dots", "file-earmark-pdf", "easel", "graph-up", "play-btn", "patch-question"],
        menu_icon="mortarboard",
        default_index=0,
    )
    
    if st.button("🔄 New Session", use_container_width=True):
        st.session_state.messages = []
        st.session_state.chat_session = None
        st.rerun()

# --- GEMINI SETUP ---
if api_key:
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("models/gemini-2.5-flash")
else:
    st.warning("⚠️ Masukkan API Key di sidebar.")
    st.stop()

# --- CORE LOGIC ---
# Handling File Uploads based on Mode
context_text = ""
uploaded_media = None
system_instruction = "Anda adalah asisten akademik dan pakar Data Science."
if "PDF" in mode:
    multiple = "Multiple" in mode
    files = st.file_uploader("Upload PDF", type="pdf", accept_multiple_files=multiple)
    if files:
        with st.spinner("Processing PDF..."):
            raw_text = get_pdf_text(files if multiple else [files])
            context_text = "\n".join(split_text(raw_text))
            st.success("PDF processed!")

if mode == "AcademicPDF Analysis":
    files = st.file_uploader("Upload Jurnal (PDF)", type="pdf", accept_multiple_files=True)
    if files:
        raw_text = get_pdf_text(files)
        context_text = "\n".join(split_text(raw_text))
        system_instruction = "Analisis paper ini. Jelaskan metodologi, kebaruan (novelty), dan keterbatasan penelitian ini."
elif mode == "🖼️ Image insight":
    file = st.file_uploader("Upload Image", type=["jpg", "jpeg", "png"])
    if file:
        uploaded_media = Image.open(file)
        st.image(uploaded_media, caption="Uploaded Image", width=300)

elif mode == "🎥 Chat with Video":
    file = st.file_uploader("Upload Video", type=["mp4", "mpeg", "mov", "avi"])
    if file:
        st.video(file)
        # Process video for Gemini
        if st.button("Process Video"):
            with st.spinner("Uploading video to Gemini..."):
                tfile = io.BytesIO(file.read())
                # Save temp for Gemini upload
                with open("temp_video.mp4", "wb") as f:
                    f.write(tfile.getbuffer())
                uploaded_media = genai.upload_file(path="temp_video.mp4")
                while uploaded_media.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_media = genai.get_file(uploaded_media.name)
                st.success("Video ready!")

elif mode == "Presentation Designer":
    system_instruction = "Buatkan struktur slide presentasi yang edukatif, menarik, dan mudah dipahami mahasiswa. Sertakan saran aset visual."

elif mode == "Data & Graph Insight":
    file = st.file_uploader("Upload Grafik/Dataset Image", type=["jpg", "png", "jpeg"])
    if file:
        uploaded_media = Image.open(file)
        st.image(uploaded_media, caption="Data Source", use_container_width=True)
        system_instruction = "Interpretasikan data ini secara statistik. Jelaskan tren yang terlihat bagi audiens awam."

elif mode == "Quiz Generator":
    system_instruction = "Berdasarkan topik atau materi yang diberikan, buatkan 5 soal pilihan ganda dan 2 soal esai beserta kunci jawabannya untuk evaluasi mahasiswa."
elif mode == "Video Translate":
  file = st.file_uploader("Upload Materi Kuliah (Video)", type=["mp4", "mov", "avi"])
  if file:
    st.video(file)
    if st.button("Proses Video"):
      with st.spinner("Gemini sedang menonton video..."):
        with open("temp_vid.mp4", "wb") as f: f.write(file.read())
        uploaded_media = genai.upload_file(path="temp_vid.mp4")
        while uploaded_media.state.name == "PROCESSING":
          time.sleep(2)
          uploaded_media = genai.get_file(uploaded_media.name)
          st.success("Video siap dianalisis!")

elif mode == "Audio Insights":
  file = st.file_uploader("Upload Rekaman Kuliah (Audio)", type=["mp3", "wav"])
  if file:
    st.audio(file)
    if st.button("Proses Audio"):
      with open("temp_aud.mp3", "wb") as f: f.write(file.read())
      uploaded_media = genai.upload_file(path="temp_aud.mp3")
      st.success("Audio siap ditranskripsi!")

# --- CHAT INTERFACE ---
for message in st.session_state.messages:
  with st.chat_message(message["role"]):
    st.markdown(message["content"])


# --- CHAT UI ---
st.title(f"📍 {mode}")

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Apa yang ingin Anda diskusikan?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Construct Query
            final_query = f"{system_instruction}\n\n"
            if context_text:
                final_query += f"Konteks Dokumen: {context_text}\n\n"
            final_query += f"Pertanyaan User: {prompt}"

            if uploaded_media:
                response = model.generate_content([final_query, uploaded_media])
            else:
                if st.session_state.chat_session is None:
                    st.session_state.chat_session = model.start_chat(history=[])
                response = st.session_state.chat_session.send_message(final_query)
            
            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Terjadi kesalahan: {e}")

