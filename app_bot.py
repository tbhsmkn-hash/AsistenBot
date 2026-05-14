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

# Custom CSS untuk tabel agar rapi
st.markdown("""
<style>
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #454d5a; padding: 8px; text-align: left; }
</style>
""", unsafe_allow_html=True)

# State Management
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- UTILITY FUNCTIONS ---
def get_pdf_text(pdf_docs):
    text = ""
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            text += f"\n--- SOURCE: {pdf.name} ---\n" # Penanda nama file
            for page in pdf_reader.pages:
              content = page.extract_text()
              if content:
                text += content
        except Exception as e:
            st.error(f"Error membaca PDF: {e}")
    return text

def split_text(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=10000, chunk_overlap=1000)
    return text_splitter.split_text(text)

# --- SIDEBAR ---
with st.sidebar:
    st.title("🧪 Academic Control Center")
    api_key = st.text_input("Enter Google API Key:", type="password")
    
    st.write("---")
    mode = option_menu(
        menu_title="Data Akademik",
        options=[
            "General Chat",
            "AcademicPDF Analysis",
            "Presentation Designer",
            "Data & Graph Insight",
            "Video Mentor",
            "Image insight",
            "Video Translate",
            "Audio Insights",
            "Quiz Generator"
        ],
        icons=["chat-dots", "file-earmark-pdf", "easel", "graph-up", "play-btn", "image", "translate", "mic", "patch-question"],
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
    # Menggunakan model yang stabil: gemini-1.5-flash
    model = genai.GenerativeModel("models/gemini-2.5-flash")
else:
    st.warning("⚠️ Masukkan API Key di sidebar.")
    st.stop()

# --- UI HEADER ---
st.title(f"📍 {mode}")
st.write("---")

# --- CORE LOGIC & UPLOAD CENTER ---
context_text = ""
uploaded_media = None
system_instruction = "Anda adalah asisten akademik dan pakar Data Science."

with st.container(border=True):
    st.subheader("📤 File Processing Center")
    
    if mode == "AcademicPDF Analysis":
        files_pdf = st.file_uploader("Upload Beberapa Jurnal (PDF)", 
                             type="pdf", 
                             accept_multiple_files=True, 
                             key="multi_pdf_uploader")
        if files_pdf:
            with st.spinner(f"Membaca {len(files_pdf)} dokumen..."):
              raw_text = get_pdf_text(files_pdf)
              context_text = "\n".join(split_text(raw_text))
              # System instruction khusus perbandingan jurnal
              system_instruction = """
              Anda adalah asisten peneliti senior. Analisis semua dokumen yang diberikan.
              Jika ada beberapa dokumen, buatkan:
              1. **Ringkasan Komprehensif**: Inti dari semua paper.
              2. **Tabel Perbandingan**: Bandingkan Metodologi, Dataset, dan Hasil dari tiap file.
              3. **Sintesis**: Apa benang merah atau perbedaan utama antar penelitian ini?
              """
              st.success(f"✅ {len(files_pdf)} PDF berhasil diproses!")

    elif mode == "🖼️ Image insight":
        file_img = st.file_uploader("Upload Gambar", type=["jpg", "jpeg", "png"], key="img_in")
        if file_img:
            uploaded_media = Image.open(file_img)
            st.image(uploaded_media, caption="Preview Image", use_container_width=True, width=300)
            system_instruction = "Anda adalah Senior Data Scientist. Analisis visualisasi data ini: Klasifikasi Visual, Tren, Anomali, dan Rekomendasi Strategis."

    elif mode == "Video Mentor" or mode == "Video Translate":
        file_vd = st.file_uploader("Upload Video", type=["mp4", "mov", "avi"], key="vid_gen")
        if file_vd:
            st.video(file_vd)
            if st.button("Proses Video dengan AI"):
                with st.spinner("Mengunggah video ke Gemini..."):
                    with open("temp_video.mp4", "wb") as f:
                        f.write(file_vd.getbuffer())
                    uploaded_media = genai.upload_file(path="temp_video.mp4")
                    while uploaded_media.state.name == "PROCESSING":
                        time.sleep(2)
                        uploaded_media = genai.get_file(uploaded_media.name)
                    st.success("Video siap dianalisis!")
            system_instruction = "Anda adalah Mentor Pembelajaran. Analisis video ini, berikan ringkasan konsep, timeline momen penting, dan Q&A."

    elif mode == "Data & Graph Insight":
        file_dt = st.file_uploader("Upload Grafik/Tabel", type=["jpg", "png", "jpeg"], key="data_graph")
        if file_dt:
            uploaded_media = Image.open(file_dt)
            st.image(uploaded_media, use_container_width=True)
            system_instruction = "Bedah grafik ini secara profesional. Identifikasi variabel, tren statistik, dan berikan insight bisnis/akademik."

    elif mode == "Audio Insights":
        file_au = st.file_uploader("Upload Audio Rekaman", type=["mp3", "wav"], key="audio_in")
        if file_au:
            st.audio(file_au)
            if st.button("Transkripsi Audio"):
                with st.spinner("Memproses audio..."):
                    with open("temp_audio.mp3", "wb") as f:
                        f.write(file_au.getbuffer())
                    uploaded_media = genai.upload_file(path="temp_audio.mp3")
                    st.success("Audio siap!")
            system_instruction = "Anda adalah Analis Audio. Berikan transkripsi poin utama, ringkasan Cornell, dan kata kunci penting."

    elif mode == "Quiz Generator":
        st.info("Ketik topik atau tempel materi di chat untuk membuat soal.")
        system_instruction = "Buatkan 10 soal pilihan ganda HOTS dan 2 soal esai lengkap dengan kunci jawaban dan pembahasan."

    elif mode == "Presentation Designer":
        system_instruction = "Buatkan struktur slide presentasi: Judul, Konten Utama, dan saran aset visual."

# --- CHAT INTERFACE ---
# Tampilkan riwayat chat
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Input Chat
if prompt := st.chat_input("Apa yang ingin Anda diskusikan?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            # Bangun prompt akhir
            final_query = f"System: {system_instruction}\n\n"
            if context_text:
                final_query += f"Context: {context_text}\n\n"
            final_query += f"User: {prompt}"

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
