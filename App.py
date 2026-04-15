from io import BytesIO
import re

import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(page_title="Verificador de Faturas", layout="wide")
st.title("Verificador de Faturas")
st.write("Carrega os PDFs e a app vai detetar Transaction numbers repetidos entre faturas diferentes.")

def extrair_transacoes_texto(uploaded_file):
    pdf_bytes = BytesIO(uploaded_file.read())
    linhas = []

    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if not text:
                continue

            lines = text.split("\n")
            for line in lines:
                if "transaction number" in line.lower():
                    nums = re.findall(r"\b\d+\b", line)
                    if len(nums) >= 1:
                        for n in nums:
                            if len(n) >= 3:
                                linhas.append({
                                    "Transaction Number": n,
                                    "File": uploaded_file.name
                                })

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
                df = extrair_transacoes_texto(file)
                if not df.empty:
                    todos.append(df)
                else:
                    st.warning(f"Não consegui extrair Transaction number de {file.name}")
            except Exception as e:
                st.error(f"Erro ao ler {file.name}: {e}")

        if not todos:
            st.warning("Não foi possível extrair dados válidos dos PDFs.")
        else:
            df_todos = pd.concat(todos, ignore_index=True)

            resumo = (
                df_todos.groupby("Transaction Number")["File"]
                .agg(lambda x: sorted(set(x)))
                .reset_index(name="Files")
            )

            resumo["num_files"] = resumo["Files"].apply(len)
            duplicados = resumo[resumo["num_files"] > 1][["Transaction Number", "Files"]].copy()

            if duplicados.empty:
                st.success("OK, tudo certo sem duplicações entre faturas.")
            else:
                duplicados["Files"] = duplicados["Files"].apply(lambda x: ", ".join(x))
                st.error("Foram encontradas duplicações entre faturas:")
                st.dataframe(duplicados, use_container_width=True)
