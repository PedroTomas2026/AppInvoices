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

            for line in text.split("\n"):
                line = line.strip()
                if not line:
                    continue

                nums = re.findall(r"\b\d+\b", line)
                if len(nums) < 2:
                    continue

                if "invoice number" in line.lower() or "invoice date" in line.lower():
                    continue
                if "total(" in line.lower():
                    continue
                if "order number" in line.lower() and "transaction number" in line.lower():
                    continue

                order_number = nums[0]
                transaction_number = nums[1]

                if len(transaction_number) < 3:
                    continue

                linhas.append(
                    {
                        "Transaction Number": transaction_number,
                        "Order Number": order_number,
                        "File": uploaded_file.name,
                    }
                )

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

            df_todos["Transaction Number"] = df_todos["Transaction Number"].astype(str).str.strip()
            df_todos["File"] = df_todos["File"].astype(str).str.strip()

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
