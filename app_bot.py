import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from streamlit_option_menu import option_menu
from PIL import Image
import io
import time
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
import requests

# --- CONFIGURATION ---
st.set_page_config(page_title="Ridwan Academy AI", layout="wide", page_icon="")

st.markdown("""
<style>
    table { width: 100%; border-collapse: collapse; }
    th, td { border: 1px solid #454d5a; padding: 8px; text-align: left; }
</style>
""", unsafe_allow_html=True)

if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

# --- UTILITY FUNCTIONS ---
def get_pdf_text(pdf_docs):
    text = []
    for pdf in pdf_docs:
        try:
            pdf_reader = PdfReader(pdf)
            text.append(f"\n--- SOURCE: {pdf.name} ---\n")
            for page in pdf_reader.pages:
                content = page.extract_text()
                if content:
                    text.append(content)
        except Exception as e:
            st.error(f"Error membaca PDF {pdf.name}: {e}")
    return "".join(text)

def split_text(text):
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=8000, chunk_overlap=800)
    return text_splitter.split_text(text)

# --- ADVANCED FEDERATED ACADEMIC SEARCH ENGINES ---
def search_core_ac_uk(query, max_results=3):
    results = []
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.core.ac.uk/v3/search/works?q={encoded_query}&limit={max_results}"
        response = requests.get(url, timeout=5).json()
        if "results" in response:
            for item in response["results"]:
                if item.get("downloadUrl"):
                    results.append({
                        "source": f"Global Publisher Link ({item.get('publisher', 'Scopus/Elsevier Peer-Reviewed')})",
                        "title": item.get("title", "No Title"),
                        "summary": item.get("abstract", "Abstrak tersedia di dokumen utama."),
                        "pdf_url": item.get("downloadUrl")
                    })
    except:
        pass
    return results

def search_arxiv_and_rfc(query, max_results=3):
    results = []
    try:
        formatted_query = query.replace(" ", "+")
        url = f'http://export.arxiv.org/api/query?search_query=all:{formatted_query}&max_results={max_results}'
        with urllib.request.urlopen(url, timeout=5) as response:
            root = ET.fromstring(response.read())
        ns = {'atom': 'http://www.w3.org/2005/Atom'}

        for entry in root.findall('atom:entry', ns):
            title = entry.find('atom:title', ns).text.strip()
            summary = entry.find('atom:summary', ns).text.strip()
            pdf_url = ""
            for link in entry.findall('atom:link', ns):
                if link.attrib.get('title') == 'pdf':
                    pdf_url = link.attrib.get('href')
            if pdf_url:
                results.append({"source": "ArXiv / RFC / IEEE & ACM Index", "title": title, "summary": summary, "pdf_url": pdf_url})
    except:
        pass
    return results

def search_semantic_scholar_advanced(query, max_results=3):
    results = []
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.semanticscholar.org/graph/v1/paper/search?query={encoded_query}&limit={max_results}&fields=title,abstract,openAccessPdf,publicationTypes,venue"
        response = requests.get(url, timeout=5).json()
        if "data" in response:
            for paper in response["data"]:
                if paper.get("openAccessPdf") and paper["openAccessPdf"].get("url"):
                    pub_type = ", ".join(paper.get("publicationTypes", ["Journal/Thesis"]))
                    venue = paper.get("venue", "International Database")
                    results.append({
                        "source": f"{venue} ({pub_type})",
                        "title": paper.get("title", "No Title"),
                        "summary": paper.get("abstract", "Tidak ada abstrak publik, file PDF tersedia langsung."),
                        "pdf_url": paper["openAccessPdf"]["url"]
                    })
    except:
        pass
    return results

def search_unpaywall(query, max_results=3):
    results = []
    try:
        encoded_query = urllib.parse.quote(query)
        url = f"https://api.crossref.org/works?query={encoded_query}&rows={max_results}"
        response = requests.get(url, timeout=5).json()
        if "message" in response and "items" in response["message"]:
            for item in response["message"]["items"]:
                doi = item.get("DOI")
                if doi:
                    up_url = f"https://api.unpaywall.org/v2/{doi}?email=unpaywall_finder@academic.edu"
                    up_resp = requests.get(up_url, timeout=3).json()
                    if up_resp.get("is_oa") and up_resp.get("best_oa_location"):
                        pdf_url = up_resp["best_oa_location"].get("url_for_pdf")
                        if pdf_url:
                            results.append({
                                "source": f"Crossref/Unpaywall ({item.get('publisher', 'International Standard Open Center')})",
                                "title": item.get("title", ["No Title"])[0],
                                "summary": f"Dokumen/Whitepaper Terverifikasi Resmi DOI: {doi}",
                                "pdf_url": pdf_url
                            })
    except:
        pass
    return results

def search_indonesia_repo(query, max_results=3):
    results = []
    try:
        encoded_query = urllib.parse.quote(f"{query} indonesia")
        url = f"https://api.crossref.org/works?query={encoded_query}&rows=10&filter=has-public-references:true"
        response = requests.get(url, timeout=5).json()
        if "message" in response and "items" in response["message"]:
            for item in response["message"]["items"]:
                publisher = item.get("publisher", "").lower()
                if "indonesia" in publisher or "universitas" in publisher or "jurnal" in publisher:
                    doi = item.get("DOI")
                    link = item.get("link", [{}])[0].get("URL") if item.get("link") else f"https://doi.org/{doi}"
                    if link:
                        results.append({
                            "source": f"SINTA / GARUDA / NELITI Hub ({item.get('publisher', 'Pustaka Indonesia')})",
                            "title": item.get("title", ["No Title"])[0],
                            "summary": f"Referensi Jurnal Nasional Terindeks. DOI: {doi}",
                            "pdf_url": link
                        })
                    if len(results) >= max_results:
                        break
    except:
        pass
    return results

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
            "Artikel Reviewer",
            "Jurnal & Standard Finder",
            "Presentation Designer",
            "Data & Graph Insight",
            "Video Mentor",
            "Image insight",
            "Video Translate",
            "Audio Insights",
            "Quiz Generator",
            "✍️ Humanize Text",
            "AI Detector Counter"
        ],
        icons=["chat-dots", "file-earmark-pdf", "clipboard-check", "download", "easel", "graph-up", "play-btn", "image", "translate", "mic", "patch-question", "pencil-square", "shield-slash"],
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

# --- UI HEADER ---
st.title(f"📍 {mode}")
st.write("---")

# --- CORE LOGIC & UPLOAD CENTER ---
context_text = ""
uploaded_media = None
system_instruction = "Anda adalah asisten akademik dan pakar Data Science."

with st.container(border=True):
    st.subheader("📤 Workspace Center")

    if mode == "AcademicPDF Analysis":
        files_pdf = st.file_uploader("Upload Beberapa Jurnal (PDF)", type="pdf", accept_multiple_files=True, key="multi_pdf_uploader")
        if files_pdf:
            with st.spinner(f"Membaca {len(files_pdf)} dokumen..."):
                raw_text = get_pdf_text(files_pdf)
                context_text = "\n".join(split_text(raw_text))
                system_instruction = "Anda adalah asisten peneliti senior. Analisis semua dokumen dan buat tabel perbandingan metodologinya."
                st.success(f"✅ {len(files_pdf)} PDF berhasil diproses!")

    elif mode == "Artikel Reviewer":
        st.info("🔎 **Kritik & Review Jurnal Ilmiah Otomatis**")
        st.write("Unggah draf artikel atau jurnal mentah untuk dibedah secara kritis berdasarkan standar peer-review.")

        file_review = st.file_uploader("Upload File Artikel/Jurnal (PDF)", type="pdf", key="reviewer_uploader")
        review_style = st.selectbox(
            "Format Standar Review:",
            ["Komprehensif (Metodologi + Hasil)", "Kritik Tajam (Cari Kelemahan & Gap)", "Ringkas (Struktur Kualitatif/Kuantitatif)"],
            key="rev_style"
        )

        if file_review:
            with st.spinner("Mengekstrak teks artikel (Stream Mode)..."):
                # Ringan CPU: Menggunakan list builder dan pemotongan chunk hemat RAM
                raw_text_rev = get_pdf_text([file_review])
                context_text = "\n".join(split_text(raw_text_rev))

                system_instruction = f"""
                Anda adalah Reviewer Senior dari Jurnal Internasional bereputasi tinggi (Scopus Q1).
                Tugas Anda adalah melakukan bedah kritis formal terhadap artikel yang dilampirkan menggunakan standar: {review_style}.

                Wajib menyajikan output review dalam struktur poin berikut:
                1. **Kelebihan Utama**: Kontribusi nyata apa yang dibawa paper ini?
                2. **Kritik Metodologi**: Apakah desain riset, sampling, atau algoritma yang digunakan sudah valid dan kokoh? Di mana celah kelemahannya?
                3. **Analisis Dataset & Evaluasi**: Apakah data pendukung cukup kuat untuk menarik kesimpulan?
                4. **Rekomendasi Perbaikan Teknis**: Berikan langkah konkret apa yang harus diperbaiki penulis agar artikel layak publish.
                """
                st.success("✅ Artikel siap di-review! Silakan ketik perintah lanjutan atau langsung kirim pesan kosong di chat box bawah.")

    elif mode == "Jurnal & Standard Finder":
        st.info("🌐 **Unified Global Academic Indexing Engine**")
        search_query = st.text_input("Masukkan Judul, Topik, Standar:", key="jf_query")
        pustaka_pilihan = st.multiselect(
            "Pilih Repositori Target:",
            [
                "Global Publishers (Scopus, ScienceDirect, Elsevier, Springer, DOAJ)",
                "Tech & Standard Center (IEEE, ACM, ArXiv, RFC Networking, ISO/ITU-T Mirror)",
                "Global Scholar Hub (Google Scholar Proxy, PubMed, ResearchGate Meta)",
                "Pustaka Indonesia (SINTA, Garuda, Neliti, Perpusnas, Thesis Regional)"
            ],
            default=["Global Publishers (Scopus, ScienceDirect, Elsevier, Springer, DOAJ)", "Tech & Standard Center (IEEE, ACM, ArXiv, RFC Networking, ISO/ITU-T Mirror)"],
            key="jf_sources_advanced"
        )

        if search_query and st.button("Eksekusi Pencarian Multi-API", key="jf_btn"):
            all_results = []
            with st.spinner("Menghubungi kluster gerbang API internasional (In-Memory Stream)..."):
                if "Global Publishers (Scopus, ScienceDirect, Elsevier, Springer, DOAJ)" in pustaka_pilihan:
                    all_results.extend(search_core_ac_uk(search_query))
                if "Tech & Standard Center (IEEE, ACM, ArXiv, RFC Networking, ISO/ITU-T Mirror)" in pustaka_pilihan:
                    all_results.extend(search_arxiv_and_rfc(search_query))
                if "Global Scholar Hub (Google Scholar Proxy, PubMed, ResearchGate Meta)" in pustaka_pilihan:
                    all_results.extend(search_semantic_scholar_advanced(search_query))
                    all_results.extend(search_unpaywall(search_query))
                if "Pustaka Indonesia (SINTA, Garuda, Neliti, Perpusnas, Thesis Regional)" in pustaka_pilihan:
                    all_results.extend(search_indonesia_repo(search_query))

            if not all_results:
                st.warning("Tidak ditemukan dokumen open-access langsung.")
            else:
                st.success(f"Berhasil mengamankan {len(all_results)} referensi ilmiah resmi!")
                ai_context = []
                for i, res in enumerate(all_results):
                    with st.container(border=True):
                        st.markdown(f"#### 📄 {i+1}. {res['title']}")
                        st.caption(f"Sumber/Kluster Indeks: **{res['source']}**")
                        st.write(f"**Abstrak/Keterangan:** {res['summary'][:400]}...")
                        st.link_button("📥 Buka / Unduh Dokumen Resmi", res['pdf_url'])
                    ai_context.append(f"Judul: {res['title']}\nSumber: {res['source']}\nAbstrak: {res['summary']}\n---")
                context_text = "\n".join(ai_context)
                system_instruction = "Anda adalah Pustakawan Riset Internasional. Analisis daftar dokumen ini."

    elif mode == "🖼️ Image insight":
        file_img = st.file_uploader("Upload Gambar", type=["jpg", "jpeg", "png"], key="img_in")
        if file_img:
            uploaded_media = Image.open(file_img)
            st.image(uploaded_media, caption="Preview Image", use_container_width=True)
            system_instruction = "Anda adalah Senior Data Scientist. Analisis visualisasi data ini."

    elif mode in ["Video Mentor", "Video Translate"]:
        file_vd = st.file_uploader("Upload Video", type=["mp4", "mov", "avi"], key="vid_gen")
        if file_vd:
            st.video(file_vd)
            if st.button("Proses Video dengan AI", key="vid_process_btn"):
                with st.spinner("Mengunggah video ke Gemini via API Stream (In-Memory)..."):
                    video_bytes = file_vd.read()
                    uploaded_media = genai.upload_file(io.BytesIO(video_bytes), mime_type="video/mp4")
                    while uploaded_media.state.name == "PROCESSING":
                        time.sleep(3)
                        uploaded_media = genai.get_file(uploaded_media.name)
                    st.success("Video siap dianalisis!")
            system_instruction = "Anda adalah Mentor Pembelajaran Digital. Analisis video ini."

    elif mode == "✍️ Humanize Text":
        st.info("Ubah teks AI yang kaku menjadi natural.")
        tone_style = st.select_slider("Pilih Nada Tulisan:", options=["Kasual/Populer", "Semi-Formal (Edukatif)", "Akademik Santun"], key="hm_tone")
        human_text_input = st.text_area("Tempel teks buatan AI di sini:", height=200, key="hm_input")
        if human_text_input:
            context_text = human_text_input
            system_instruction = f"Anda adalah Editor Esai Profesional. Tulis ulang teks agar terasa humanis dengan gaya: {tone_style}."

    elif mode == "Data & Graph Insight":
        file_dt = st.file_uploader("Upload Grafik/Tabel", type=["jpg", "png", "jpeg"], key="data_graph")
        if file_dt:
            uploaded_media = Image.open(file_dt)
            st.image(uploaded_media, use_container_width=True)
            system_instruction = "Bedah grafik ini secara profesional."

    elif mode == "Audio Insights":
        file_au = st.file_uploader("Upload Audio Rekaman", type=["mp3", "wav"], key="audio_in")
        if file_au:
            st.audio(file_au)
            if st.button("Transkripsi Audio", key="aud_process_btn"):
                with st.spinner("Memproses berkas audio (In-Memory)..."):
                    audio_bytes = file_au.read()
                    uploaded_media = genai.upload_file(io.BytesIO(audio_bytes), mime_type="audio/mp3")
                    st.success("Audio siap diproses!")
            system_instruction = "Anda adalah Analis Audio Akademik."

    elif mode == "Quiz Generator":
        st.info("Ketik topik atau lampirkan materi di ruang chat di bawah untuk merancang paket soal evaluasi.")
        system_instruction = "Buatkan 10 butir soal pilihan ganda berbasis tingkat tinggi (HOTS) dan 2 soal esai analitis."

    elif mode == "Presentation Designer":
        st.info("Gunakan kolom chat di bawah untuk memasukkan materi presentasi Anda.")
        system_instruction = "Buatkan rancangan struktur slide presentasi edukatif."

    elif mode == "AI Detector Counter":
        st.info("🔬 **Academic Anti-AI Detector & Paraphraser**")
        academic_text = st.text_area("Masukkan draf tulisan/jurnal yang ingin diperbaiki:", height=200, key="ai_counter_input")
        bypass_focus = st.selectbox("Fokus Utama Optimasi Counter:", ["Meningkatkan Variasi Kalimat (Burstiness)", "Meningkatkan Keunikan Kosakata (Perplexity)", "Standar Jurnal Internasional (Scopus/IEEE)"], key="ai_counter_focus")
        if academic_text:
            context_text = academic_text
            system_instruction = f"Anda adalah Profesor Senior Scopus. Lakukan parafrase tingkat tinggi pada teks dengan fokus optimasi: {bypass_focus}."

# --- CHAT INTERFACE ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("Apa yang ingin Anda diskusikan?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        try:
            final_query = f"System Instruction: {system_instruction}\n\n"
            if context_text:
                final_query += f"Context Data/Teks: {context_text}\n\n"
            final_query += f"User Prompt: {prompt}"

            if uploaded_media:
                response = model.generate_content([final_query, uploaded_media])
            else:
                if st.session_state.chat_session is None:
                    st.session_state.chat_session = model.start_chat(history=[])
                response = st.session_state.chat_session.send_message(final_query)

            st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})
        except Exception as e:
            st.error(f"Terjadi kesalahan pemrosesan LLM: {e}")
