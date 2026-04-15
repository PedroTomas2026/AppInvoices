import streamlit as st
import pandas as pd
import pdfplumber
from io import BytesIO

st.set_page_config(page_title="Verificador de Faturas", layout="wide")
st.title("Verificador de Faturas")
st.write("Faz upload das faturas em PDF e a app vai detetar Transaction numbers repetidos entre ficheiros diferentes.")

def normalizar_coluna(nome):
    return str(nome).strip().lower().replace("\n", " ")

def ler_pdf(uploaded_file):
    linhas = []
    pdf_bytes = BytesIO(uploaded_file.read())

    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tab in tables:
                if not tab or len(tab) < 2:
                    continue

                header = [normalizar_coluna(c) for c in tab[0]]
                if not any("transaction number" in c for c in header):
                    continue

                try:
                    idx_trx = next(i for i, c in enumerate(header) if "transaction number" in c)
                except StopIteration:
                    continue

                for row in tab[1:]:
                    if idx_trx >= len(row):
                        continue
                    trx = row[idx_trx]
                    if trx is None:
                        continue
                    trx = str(trx).strip()
                    if trx:
                        linhas.append({"Transaction Number": trx, "File": uploaded_file.name})

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
                    st.warning(f"Não foi encontrada a coluna Transaction number em {file.name}")
            except Exception as e:
                st.error(f"Erro ao ler {file.name}: {e}")

        if todos:
            df_todos = pd.concat(todos, ignore_index=True)

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
