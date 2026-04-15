import re
from io import BytesIO

import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(page_title="Verificador de Faturas", layout="wide")
st.title("Verificador de Faturas")
st.write("Carrega os PDFs e a app vai procurar Transaction numbers repetidos entre faturas diferentes.")

def limpar_texto(x):
    return str(x).strip().replace("\n", " ")

def extrair_por_tabela(page, filename):
    linhas = []
    tables = page.extract_tables()
    for tab in tables:
        if not tab or len(tab) < 2:
            continue

        header = [limpar_texto(c).lower() for c in tab[0]]
        if not any("transaction" in c and "number" in c for c in header):
            continue

        try:
            idx = next(i for i, c in enumerate(header) if "transaction" in c and "number" in c)
        except StopIteration:
            continue

        for row in tab[1:]:
            if idx >= len(row):
                continue
            trx = limpar_texto(row[idx])
            if trx and trx.lower() != "none":
                linhas.append({"Transaction Number": trx, "File": filename})
    return linhas

def extrair_por_texto(page, filename):
    linhas = []
    texto = page.extract_text() or ""
    for line in texto.split("\n"):
        if "transaction" in line.lower() and "number" in line.lower():
            m = re.search(r"transaction\s*number[:\s]*([A-Za-z0-9\-_.]+)", line, re.I)
            if m:
                trx = m.group(1).strip()
                if trx:
                    linhas.append({"Transaction Number": trx, "File": filename})
    return linhas

def ler_pdf(uploaded_file):
    linhas = []
    pdf_bytes = BytesIO(uploaded_file.read())

    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            linhas.extend(extrair_por_tabela(page, uploaded_file.name))
            if not linhas:
                linhas.extend(extrair_por_texto(page, uploaded_file.name))

    return pd.DataFrame(linhas)

uploaded_files = st.file_uploader(
    "Carrega os PDFs das faturas",
    type=["pdf"],
    accept_multiple_files=True
)

if st.button("Verificar duplicados"):
    if not uploaded_files:
        st.warning("Carrega pelo menos um PDF.")
    else:
        todos = []
        for file in uploaded_files:
            try:
                df = ler_pdf(file)
                if not df.empty:
                    todos.append(df)
                else:
                    st.warning(f"Não consegui extrair Transaction number de {file.name}")
            except Exception as e:
                st.error(f"Erro ao ler {file.name}: {e}")

        if todos:
            df_todos = pd.concat(todos, ignore_index=True)
            df_todos["Transaction Number"] = df_todos["Transaction Number"].astype(str).str.strip()
            df_todos = df_todos[df_todos["Transaction Number"] != ""]

            grouped = (
                df_todos.groupby("Transaction Number")["File"]
                .agg(lambda x: sorted(set(x)))
                .reset_index()
            )
            grouped["num_files"] = grouped["File"].str.len()

            dup_btw = grouped[grouped["num_files"] > 1]

            if dup_btw.empty:
                st.success("OK, tudo certo sem duplicações entre faturas.")
            else:
                st.error("Foram encontradas duplicações entre faturas:")
                st.dataframe(dup_btw[["Transaction Number", "File"]], use_container_width=True)
        else:
            st.warning("Não foi possível extrair dados válidos dos PDFs.")
