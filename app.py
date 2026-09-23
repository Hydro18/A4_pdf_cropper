import streamlit as st
import fitz  # PyMuPDF

A4_WIDTH, A4_HEIGHT = fitz.paper_size("a4")
PADDING = 10
MARGIN_A4 = 25


def content_rect(page):
    """Rettangolo che contiene tutto ciò che è disegnato sulla pagina.

    get_bboxlog() è calcolato in C: molto più veloce di get_drawings(),
    che costruisce un dizionario Python per ogni singolo tratto di penna.
    """
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height
    crop = None

    for kind, bbox in page.get_bboxlog():
        r = fitz.Rect(bbox) & page_rect
        if r.is_empty:
            continue
        # Testo invisibile (es. livello OCR): non conta come contenuto
        if kind == "ignore-text":
            continue
        # Sfondi a tutta pagina (riempimento bianco, carta dell'app di note)
        if kind.startswith("fill") and kind != "fill-text" \
                and r.width * r.height > 0.9 * page_area:
            continue
        crop = r if crop is None else crop | r

    if crop is None:
        return page_rect

    crop = (crop + (-PADDING, -PADDING, PADDING, PADDING)) & page_rect
    if crop.width <= 0 or crop.height <= 0:
        return page_rect
    return crop


def crop_and_maximize_a4(input_pdf_bytes: bytes) -> bytes:
    doc_in = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    doc_out = fitz.open()
    try:
        avail_w = A4_WIDTH - 2 * MARGIN_A4
        avail_h = A4_HEIGHT - 2 * MARGIN_A4

        for page_num, page_in in enumerate(doc_in):
            crop_rect = content_rect(page_in)
            cw, ch = crop_rect.width, crop_rect.height

            scale = min(avail_w / cw, avail_h / ch)
            final_w, final_h = cw * scale, ch * scale
            x0 = (A4_WIDTH - final_w) / 2
            y0 = (A4_HEIGHT - final_h) / 2
            target_rect = fitz.Rect(x0, y0, x0 + final_w, y0 + final_h)

            page_out = doc_out.new_page(width=A4_WIDTH, height=A4_HEIGHT)
            page_out.show_pdf_page(target_rect, doc_in, page_num, clip=crop_rect)

        # garbage + deflate: elimina oggetti duplicati e comprime -> file molto più leggero
        return doc_out.tobytes(garbage=3, deflate=True)
    finally:
        doc_in.close()
        doc_out.close()


# --- Interfaccia Web Mobile-Friendly ---
st.title("📱 PDF Mobile Cropper")
st.write("Elimina i bordi vuoti e impagina i tuoi appunti in un perfetto A4.")

uploaded_file = st.file_uploader("📂 Scegli un file PDF", type="pdf")

if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
    st.session_state.last_file_id = None

if uploaded_file is None:
    st.session_state.pdf_bytes = None
    st.session_state.last_file_id = None
else:
    # file_id cambia a ogni nuovo caricamento, anche se il nome è lo stesso
    file_id = getattr(uploaded_file, "file_id", f"{uploaded_file.name}-{uploaded_file.size}")
    if st.session_state.last_file_id != file_id:
        st.session_state.pdf_bytes = None
        st.session_state.last_file_id = file_id

    st.success("File caricato!")

    if st.button("✂️ Elabora e Ingrandisci", type="primary", use_container_width=True):
        with st.spinner("Elaborazione in corso..."):
            try:
                st.session_state.pdf_bytes = crop_and_maximize_a4(uploaded_file.getvalue())
            except Exception as e:
                st.session_state.pdf_bytes = None
                st.error(f"Errore durante l'elaborazione: {e}")

    if st.session_state.pdf_bytes is not None:
        file_size_mb = len(st.session_state.pdf_bytes) / (1024 * 1024)
        st.success(f"✅ PDF pronto! (Dimensione: {file_size_mb:.2f} MB)")

        safe_filename = "A4_" + "".join(
            c for c in uploaded_file.name if c.isalnum() or c in "._- "
        )

        st.download_button(
            label="📲 SCARICA IL PDF A4",
            data=st.session_state.pdf_bytes,
            file_name=safe_filename,
            mime="application/pdf",   # il telefono riconosce subito il PDF
            on_click="ignore",        # niente rerun: il link di download resta valido
            type="primary",
            use_container_width=True,
        )
