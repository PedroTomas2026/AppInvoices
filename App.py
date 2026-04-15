from io import BytesIO

import pandas as pd
import pdfplumber
import streamlit as st

st.set_page_config(page_title="Verificador de Faturas", layout="wide")
st.title("Verificador de Faturas")

st.write("Carrega os PDFs e a app vai detetar Transaction numbers repetidos entre faturas diferentes.")

def limpar_texto(x):
    return str(x).strip().replace("\n", " ")

def extrair_transacoes_pdf(uploaded_file):
    linhas = []
    pdf_bytes = BytesIO(uploaded_file.read())

    with pdfplumber.open(pdf_bytes) as pdf:
        for page in pdf.pages:
            tables = page.extract_tables()
            for tab in tables:
                if not tab or len(tab) < 2:
                    continue

                header = [limpar_texto(c).lower() for c in tab[0]]

                if "transaction number" not in " ".join(header):
                    continue

                try:
                    idx_trx = header.index("transaction number")
                except ValueError:
                    continue

                for row in tab[1:]:
                    if idx_trx >= len(row):
                        continue

                    trx = limpar_texto(row[idx_trx])

                    if not trx:
                        continue

                    if trx.lower() in {"fulfill", "file", "transaction number"}:
                        continue

                    if not trx.isdigit():
                        continue

                    linhas.append({
                        "Transaction Number": trx,
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
                df = extrair_transacoes_pdf(file)
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
