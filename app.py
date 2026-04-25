import streamlit as st
import fitz  # PyMuPDF
import io
import base64

def crop_and_maximize_a4(input_pdf_bytes):
    doc_in = fitz.open(stream=input_pdf_bytes, filetype="pdf")
    doc_out = fitz.open()
    A4_WIDTH, A4_HEIGHT = fitz.paper_size("a4")
    
    for page_num in range(len(doc_in)):
        page_in = doc_in[page_num]
        bboxes = []
        
        for block in page_in.get_text("blocks"): bboxes.append(fitz.Rect(block[:4]))
        for img in page_in.get_image_info(): bboxes.append(fitz.Rect(img["bbox"]))
        for path in page_in.get_drawings(): bboxes.append(fitz.Rect(path["rect"]))
            
        if bboxes:
            crop_rect = bboxes[0]
            for bbox in bboxes[1:]: crop_rect |= bbox
            padding = 10
            crop_rect = crop_rect + (-padding, -padding, padding, padding)
            crop_rect &= page_in.rect
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
            
    output_pdf = io.BytesIO()
    doc_out.save(output_pdf)
    return output_pdf.getvalue()

# --- Interfaccia Web Mobile-Friendly ---
st.title("📱 PDF Mobile Cropper")
st.write("Elimina i bordi vuoti e impagina i tuoi appunti in un perfetto A4.")

uploaded_file = st.file_uploader("📂 Scegli un file PDF", type="pdf")

if uploaded_file is not None:
    st.success("File caricato!")
    
    # Inizializziamo lo stato per ricordare se il PDF è stato elaborato
    if "pdf_bytes" not in st.session_state:
        st.session_state.pdf_bytes = None

    # BOTTONE 1: type="primary" lo colora, use_container_width=True lo fa largo
    if st.button("✂️ Elabora e Ingrandisci", type="primary", use_container_width=True):
        with st.spinner("Lavoro in corso..."):
            # Salviamo il risultato nella memoria della sessione
            st.session_state.pdf_bytes = crop_and_maximize_a4(uploaded_file.read())
            
    # BOTTONE 2: Fuori dall'if precedente! Compare solo se c'è un PDF pronto in memoria.
    if st.session_state.pdf_bytes is not None:
        st.info("💡 Su smartphone: clicca qui per aprire il menu del telefono e scegliere 'Salva su File' o condividerlo.")
        
        # Converte i byte del PDF in stringa Base64 in modo sicuro
        import base64
        b64_pdf = base64.b64encode(st.session_state.pdf_bytes).decode('utf-8')
        safe_filename = f"A4_{uploaded_file.name}".replace("'", "").replace('"', "")
        
        # Iniettiamo codice HTML e Javascript nativo per forzare il sistema operativo
        html_code = f"""
        <button id="custom-download-btn" style="width: 100%; padding: 14px; background-color: #FF4B4B; color: white; border: none; border-radius: 8px; font-size: 16px; font-weight: bold; cursor: pointer; font-family: sans-serif;">
            📲 SALVA O CONDIVIDI PDF
        </button>

        <script>
            // Isola il bottone per evitare conflitti con Streamlit
            const btn = document.getElementById('custom-download-btn');
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);

            newBtn.addEventListener('click', async () => {{
                try {{
                    const b64Data = "{b64_pdf}";
                    const filename = "{safe_filename}";

                    // 1. Crea il Blob per evitare il crash della memoria
                    const res = await fetch("data:application/pdf;base64," + b64Data);
                    const blob = await res.blob();
                    const file = new File([blob], filename, {{ type: 'application/pdf' }});

                    // 2. Tenta di aprire il menu nativo di iOS/Android (Web Share API)
                    if (navigator.canShare && navigator.canShare({{ files: [file] }})) {{
                        await navigator.share({{
                            files: [file],
                            title: filename
                        }});
                    }} else {{
                        // 3. Sistema di emergenza se il menu non è supportato: scarica il Blob leggero
                        const blobUrl = URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = blobUrl;
                        a.download = filename;
                        document.body.appendChild(a);
                        a.click();
                        URL.revokeObjectURL(blobUrl);
                    }}
                }} catch (error) {{
                    alert("Errore nel salvataggio: " + error.message);
                }}
            }});
        </script>
        """
        
        # unsafe_allow_html=True ci permette di far girare Javascript senza restrizioni
        st.markdown(html_code, unsafe_allow_html=True)
