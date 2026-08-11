import streamlit as st
import fitz  # PyMuPDF
import io

def crop_and_maximize_a4(input_pdf_bytes):
    # Apre il documento in input dai byte caricati
    doc_in = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    doc_out = fitz.open()
    A4_WIDTH, A4_HEIGHT = fitz.paper_size("a4")

    for page_num in range(len(doc_in)):
        page_in = doc_in[page_num]
        bboxes = []

        # 1. Recupero testo e immagini
        for block in page_in.get_text("blocks"): 
            bboxes.append(fitz.Rect(block[:4]))
        for img in page_in.get_image_info(): 
            bboxes.append(fitz.Rect(img["bbox"]))
        
        # 2. OTTIMIZZAZIONE CRITICA: Estrazione veloce dei confini dei disegni (tratti di penna)
        drawings = page_in.get_drawings()
        if drawings:
            x0 = min(d["rect"].x0 for d in drawings)
            y0 = min(d["rect"].y0 for d in drawings)
            x1 = max(d["rect"].x1 for d in drawings)
            y1 = max(d["rect"].y1 for d in drawings)
            bboxes.append(fitz.Rect(x0, y0, x1, y1))

        # Calcolo del rettangolo di ritaglio
        if bboxes:
            crop_rect = bboxes[0]
            for bbox in bboxes[1:]: 
                crop_rect |= bbox
            
            padding = 10
            crop_rect = crop_rect + (-padding, -padding, padding, padding)
            crop_rect &= page_in.rect  # Evita di sforare i bordi originali del documento
            
            # Sicurezza: se il rettangolo calcolato è invalido, mantieni la pagina intera
            if crop_rect.width <= 0 or crop_rect.height <= 0:
                crop_rect = page_in.rect
        else:
            crop_rect = page_in.rect

        page_out = doc_out.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        cw, ch = crop_rect.width, crop_rect.height

        margin_a4 = 25 
        avail_w, avail_h = A4_WIDTH - 2 * margin_a4, A4_HEIGHT - 2 * margin_a4

        scale = min(avail_w / cw, avail_h / ch)
        final_w, final_h = cw * scale, ch * scale

        x0 = (A4_WIDTH - final_w) / 2
        y0 = (A4_HEIGHT - final_h) / 2
        target_rect = fitz.Rect(x0, y0, x0 + final_w, y0 + final_h)

        page_out.show_pdf_page(target_rect, doc_in, page_num, clip=crop_rect)

    # Salvataggio in memoria
    output_pdf = io.BytesIO()
    doc_out.save(output_pdf)
    
    # 3. PULIZIA DELLA MEMORIA: Previene i crash del server (Out of Memory)
    doc_in.close()
    doc_out.close()
    
    return output_pdf.getvalue()

# --- Interfaccia Web Mobile-Friendly ---
st.title("📱 PDF Mobile Cropper")
st.write("Elimina i bordi vuoti e impagina i tuoi appunti in un perfetto A4.")

uploaded_file = st.file_uploader("📂 Scegli un file PDF", type="pdf")

# 4. GESTIONE STATO: Reset se viene caricato un file diverso dal precedente
if "last_filename" not in st.session_state:
    st.session_state.last_filename = None

if uploaded_file is not None:
    # Se l'utente ha caricato un nuovo file, resettiamo il PDF generato in precedenza
    if st.session_state.last_filename != uploaded_file.name:
        st.session_state.pdf_bytes = None
        st.session_state.last_filename = uploaded_file.name
        
    st.success("File caricato!")

    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None

    # Tasto di elaborazione
    if st.button("✂️ Elabora e Ingrandisci", type="primary", use_container_width=True):
        with st.spinner("Lavoro in corso... Elaborazione dei tratti in corso!"):
            uploaded_file.seek(0)
            st.session_state.pdf_bytes = crop_and_maximize_a4(uploaded_file.read())

    # Tasto di download (appare solo se l'elaborazione ha avuto successo)
    if st.session_state.pdf_bytes is not None:
        file_size_mb = len(st.session_state.pdf_bytes) / (1024 * 1024)

        st.success(f"✅ PDF pronto! (Dimensione: {file_size_mb:.2f} MB)")
        st.info("💡 Su smartphone: usa Chrome o Safari. Alcuni browser come Firefox Mobile bloccano i download.")

        safe_filename = f"A4_{uploaded_file.name}".replace("'", "").replace('"', "")

        st.download_button(
            label="📲 SCARICA IL PDF A4",
            data=st.session_state.pdf_bytes,
            file_name=safe_filename,
            mime="application/octet-stream",
            type="primary",
            use_container_width=True
        )
