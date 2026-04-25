import streamlit as st
import fitz  # PyMuPDF
import io

def crop_and_maximize_a4(input_pdf_bytes):
    # Carica il PDF originale
    doc_in = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    # Crea il nuovo PDF di output
    doc_out = fitz.open()
    
    # Dimensioni standard A4
    A4_WIDTH, A4_HEIGHT = fitz.paper_size("a4")
    
    for page_num in range(len(doc_in)):
        page_in = doc_in[page_num]
        bboxes = []
        
        # 1. Trova le coordinate di tutto il contenuto utile
        for block in page_in.get_text("blocks"):
            bboxes.append(fitz.Rect(block[:4]))
        for img in page_in.get_image_info():
            bboxes.append(fitz.Rect(img["bbox"]))
        for path in page_in.get_drawings():
            bboxes.append(fitz.Rect(path["rect"]))
            
        if bboxes:
            crop_rect = bboxes[0]
            for bbox in bboxes[1:]:
                crop_rect |= bbox
                
            # Piccolo margine di sicurezza per non tagliare le sbavature della penna
            padding = 10
            crop_rect = crop_rect + (-padding, -padding, padding, padding)
            crop_rect &= page_in.rect
        else:
            crop_rect = page_in.rect

        # 2. Crea la nuova pagina A4
        page_out = doc_out.new_page(width=A4_WIDTH, height=A4_HEIGHT)
        
        cw = crop_rect.width
        ch = crop_rect.height
        
        # 3. Calcolo dello Zoom Massimo
        # Imposta il margine bianco fisso che vuoi mantenere sui lati dell'A4 finale
        margin_a4 = 25 
        avail_w = A4_WIDTH - 2 * margin_a4
        avail_h = A4_HEIGHT - 2 * margin_a4
        
        # Questa è la vera magia: calcola la scala massima possibile senza distorcere l'immagine.
        # Rimuovendo il "min(1.0, ...)" permettiamo allo script di fare uno zoom-in!
        scale = min(avail_w / cw, avail_h / ch)
        
        final_w = cw * scale
        final_h = ch * scale
        
        # 4. Calcolo delle coordinate per la centratura perfetta
        x0 = (A4_WIDTH - final_w) / 2
        y0 = (A4_HEIGHT - final_h) / 2
        target_rect = fitz.Rect(x0, y0, x0 + final_w, y0 + final_h)
        
        # 5. Incolla il blocco ritagliato, scalato e centrato
        page_out.show_pdf_page(target_rect, doc_in, page_num, clip=crop_rect)
            
    output_pdf = io.BytesIO()
    doc_out.save(output_pdf)
    return output_pdf.getvalue()

# --- Interfaccia Web ---
st.title("🔍 PDF Auto-Zoom & A4 Formatter")
st.write("Carica un PDF: il tool eliminerà i bordi vuoti, ingrandirà gli appunti al massimo e li centrerà su fogli A4 pronti per la stampa.")

uploaded_file = st.file_uploader("Scegli un file PDF", type="pdf")

if uploaded_file is not None:
    st.success("File caricato correttamente!")
    
    if st.button("Ottimizza e Ingrandisci"):
        with st.spinner("Analisi, ritaglio e ingrandimento delle pagine in corso..."):
            cropped_bytes = crop_and_maximize_a4(uploaded_file.read())
            
        st.download_button(
            label="⬇️ Scarica il PDF Ottimizzato",
            data=cropped_bytes,
            file_name=f"{uploaded_file.name}_cropped",
            mime="application/pdf"
        )