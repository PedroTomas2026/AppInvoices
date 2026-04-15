from io import BytesIO

import pdfplumber
import streamlit as st

st.set_page_config(page_title="Debug Invoice", layout="wide")
st.title("Debug da Invoice")

uploaded_file = st.file_uploader("Carrega 1 PDF", type=["pdf"])

if uploaded_file:
    pdf_bytes = BytesIO(uploaded_file.read())

    with pdfplumber.open(pdf_bytes) as pdf:
        if len(pdf.pages) > 0:
            page = pdf.pages[0]
            text = page.extract_text()

            st.subheader("Texto bruto da primeira página")
            st.text(text if text else "Sem texto extraído")

            st.subheader("Tabela bruta da primeira página")
            tables = page.extract_tables()
            st.write(tables if tables else "Sem tabelas extraídas")
