import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="Painel de Leads WhatsApp", layout="wide")
st.title("📊 Painel de Leads Respondidos - WhatsApp")

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

# Carregar dados
df_respostas = carregar_respostas()

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
st.subheader("📋 Detalhamento de Leads")
st.dataframe(df_respostas, use_container_width=True)
