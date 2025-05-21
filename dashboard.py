import os
PORT = int(os.environ.get("PORT", 8501))
os.environ["STREAMLIT_SERVER_PORT"] = str(PORT)
os.environ["STREAMLIT_SERVER_HEADLESS"] = "true"

import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Painel de Leads WhatsApp", layout="wide")
st.title("\U0001F4CA Painel de Leads Respondidos - WhatsApp")

# ✨ Função para criar a tabela, se não existir
def inicializar_banco():
    try:
        conn = sqlite3.connect("respostas.db")
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS respostas (
                telefone TEXT PRIMARY KEY,
                ultima_resposta TEXT,
                atualizado_em TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Erro ao inicializar o banco: {e}")

# ✨ Backup automático para CSV
def exportar_backup_csv(df):
    try:
        if not df.empty:
            df.to_csv("backup_respostas.csv", index=False)
            st.success("Backup exportado para 'backup_respostas.csv'")
    except Exception as e:
        st.warning(f"Erro ao exportar backup: {e}")

# Função para carregar os dados do banco
@st.cache_data
def carregar_respostas():
    try:
        conn = sqlite3.connect("respostas.db")
        df = pd.read_sql_query("SELECT telefone, ultima_resposta FROM respostas", conn)
        conn.close()
        df["ultima_resposta"] = pd.to_datetime(df["ultima_resposta"])
        df = df.sort_values(by="ultima_resposta", ascending=False)
        return df
    except Exception as e:
        st.error(f"Erro ao carregar o banco de dados: {e}")
        return pd.DataFrame(columns=["telefone", "ultima_resposta"])

# Inicializar banco e carregar dados
inicializar_banco()
df_respostas = carregar_respostas()
exportar_backup_csv(df_respostas)

# KPIs
col1, col2 = st.columns(2)

with col1:
    st.metric("Total de leads respondidos", len(df_respostas))

with col2:
    if not df_respostas.empty:
        ultima = df_respostas["ultima_resposta"].max().strftime("%d/%m/%Y %H:%M")
        st.metric("Última resposta enviada", ultima)

st.divider()

# Tabela completa
st.subheader("\U0001F4CB Detalhamento de Leads")
st.dataframe(df_respostas, use_container_width=True)
