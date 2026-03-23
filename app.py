import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
from models import init_db, Usuario, Transacao, Ativo, MetaFinanceira
from engine import FinanceEngine
from datetime import datetime

# --- SETUP INICIAL & DESIGN CONSISTENTE ---
st.set_page_config(page_title="Wealth Management OS", layout="wide", page_icon="💠")
session = init_db()
eng = FinanceEngine()

# CSS para interface Sênior e Sombreada
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #161b22;
        border: 1px solid #30363d;
        padding: 15px 20px;
        border-radius: 8px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stSidebar { background-color: #0d1117; }
    div[data-testid="stExpander"] { border: 1px solid #30363d; background: #161b22; border-radius: 8px; }
    hr { margin-top: 1.5em; margin-bottom: 1.5em; border-color: #30363d; }
</style>
""", unsafe_allow_html=True)

# Garante existência do usuário master
user = session.query(Usuario).first()
if not user:
    user = Usuario(nome="Master User")
    session.add(user)
    session.commit()
    user = session.query(Usuario).first()

# --- SIDEBAR NAVIGATION ---
with st.sidebar:
    st.title("💵 Gerenciamento Financeiro - Fabio")
    
    menu = st.radio("Sistemas Ativos", [
        "Dashboard Analítico", 
        "Fluxo de Caixa",
        "Metas & Envelope", 
        "Smart Rebalance", 
        "Simulador FIRE",
        "⚙️ Configurações"
    ])
    
    st.divider()
    st.markdown("### Parâmetros de Tempo")
    sel_mes = st.selectbox("Mês de Referência", list(range(1, 13)), index=datetime.now().month-1)
    sel_ano = st.number_input("Ano de Referência", value=datetime.now().year)
    ref = f"{sel_mes:02d}/{sel_ano}"
    
    uteis = eng.calcular_dias_uteis(sel_mes, sel_ano)
    st.success(f"📅 **Neste mês temos:**\n# {uteis} Dias Úteis\n\n*(Exclui sábados, domingos e feriados nacionais)*")

# ==========================================
# 1. DASHBOARD MASTER
# ==========================================
if menu == "Dashboard Analítico":
    st.title("🎯 Visão Estratégica e Liquidez")
    st.caption("Acompanhamento de receita projetada contra despesas reais do período.")
    
    bruto_previsto = uteis * user.horas_dia * user.valor_hora
    liquido_previsto = eng.calcular_irrf_2026(bruto_previsto)
    
    trans = session.query(Transacao).filter(Transacao.mes_ano == ref).all()
    df_t = pd.DataFrame([vars(t) for t in trans]) if trans else pd.DataFrame()
    
    if not df_t.empty:
        gastos_essenciais = df_t[(df_t['tipo'] == 'Despesa') & (df_t['natureza'] == 'Essencial')]['valor'].sum()
        gastos_lifestyle = df_t[(df_t['tipo'] == 'Despesa') & (df_t['natureza'] == 'Estilo de Vida')]['valor'].sum()
        receitas_extra = df_t[df_t['tipo'] == 'Receita']['valor'].sum()
    else:
        gastos_essenciais = gastos_lifestyle = receitas_extra = 0
        
    total_receita = liquido_previsto + receitas_extra
    sobra = total_receita - (gastos_essenciais + gastos_lifestyle)
    
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Receita Líquida (Projetada + Extra)", f"R$ {total_receita:,.2f}", help=f"Baseado em {uteis} dias úteis trabalhados.")
    
    eficiencia = (gastos_essenciais+gastos_lifestyle)/total_receita*100 if total_receita>0 else 0
    limite_saudavel = user.limite_essencial + user.limite_lifestyle
    c2.metric("Nível de Gasto", f"{eficiencia:.1f}%", 
              delta=f"Ideal, menor que: {limite_saudavel}%", 
              delta_color="inverse" if eficiencia > limite_saudavel else "normal")
    
    c3.metric("Capacidade de Aporte (Sobra)", f"R$ {sobra:,.2f}", 
              delta="Superávit" if sobra > 0 else "Déficit", 
              delta_color="normal" if sobra > 0 else "inverse")
    
    c4.metric("Cotação Dólar Atual", f"R$ {eng.get_usd():,.2f}")

    st.divider()
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.subheader("🛡️ Termômetro de Reserva de Emergência")
        st.caption("Sua blindagem contra imprevistos baseada apenas em Renda Fixa.")
        ativos_rf = session.query(Ativo).filter(Ativo.classe == 'Renda Fixa').all()
        patrimonio_rf = sum([a.quantidade * a.preco_medio for a in ativos_rf])
        
        meses_cobertos = patrimonio_rf / gastos_essenciais if gastos_essenciais > 0 else 0
        progresso = min(meses_cobertos / user.reserva_meses, 1.0) if user.reserva_meses > 0 else 0
        
        st.progress(progresso)
        if meses_cobertos >= user.reserva_meses:
            st.success(f"**Blindado!** Você possui {meses_cobertos:.1f} meses de sobrevivência garantidos.")
        else:
            falta = (user.reserva_meses * gastos_essenciais) - patrimonio_rf
            st.warning(f"**Atenção:** Você tem {meses_cobertos:.1f} meses cobertos. Faltam R$ {max(0, falta):,.2f}.")

    with col2:
        st.subheader("⚖️ Distribuição do Dinheiro")
        fig_pie = px.pie(names=['Essencial', 'Lifestyle', 'Sobra/Investimento'], 
                         values=[gastos_essenciais, gastos_lifestyle, max(0, sobra)],
                         hole=0.6, color_discrete_sequence=['#ff4b4b', '#ffa421', '#00c04b'])
        fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), height=250, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
        st.plotly_chart(fig_pie, use_container_width=True)

# ==========================================
# 2. FLUXO DE CAIXA & IMPORTAÇÃO
# ==========================================
elif menu == "Fluxo de Caixa":
    st.title("💸 Gestão Diária de Caixa")
    tab1, tab2 = st.tabs(["📂 Importação Expressa (CSV)", "➕ Lançamento Manual"])
    
    with tab1:
        st.markdown("Faça upload do extrato do seu banco em `.csv`. O sistema deduzirá a categoria para você aprovar.")
        arq = st.file_uploader("Envie seu extrato CSV", type=['csv'])
        
        if arq:
            df_imp = pd.read_csv(arq, sep=None, engine='python')
            c1, c2, c3 = st.columns(3)
            col_data = c1.selectbox("Coluna Data", df_imp.columns)
            col_desc = c2.selectbox("Coluna Descrição", df_imp.columns)
            col_val = c3.selectbox("Coluna Valor", df_imp.columns)
            
            if st.button("Categorizar Automaticamente", type="primary"):
                df_clean = pd.DataFrame()
                try:
                    df_clean['Data'] = pd.to_datetime(df_imp[col_data], dayfirst=True).dt.date
                except:
                    df_clean['Data'] = datetime.now().date()
                    
                df_clean['Descrição'] = df_imp[col_desc]
                valores = df_imp[col_val].astype(str).str.replace(',', '.').astype(float)
                df_clean['Valor'] = valores.abs()
                df_clean['Tipo'] = valores.apply(lambda x: "Despesa" if x < 0 else "Receita")
                df_clean[['Categoria', 'Natureza']] = df_clean['Descrição'].apply(lambda x: pd.Series(eng.auto_categorizar(x)))
                st.session_state['df_processado'] = df_clean

        if 'df_processado' in st.session_state:
            st.success("🤖 Pronto! Valide os dados e salve.")
            df_final = st.data_editor(st.session_state['df_processado'], use_container_width=True, num_rows="dynamic")
            
            if st.button("💾 Salvar Lançamentos"):
                for _, row in df_final.iterrows():
                    nova_t = Transacao(data=row['Data'], mes_ano=row['Data'].strftime("%m/%Y"),
                        descricao=row['Descrição'], categoria=row['Categoria'], 
                        tipo=row['Tipo'], natureza=row['Natureza'], valor=row['Valor'])
                    session.add(nova_t)
                session.commit()
                del st.session_state['df_processado']
                st.rerun()

    with tab2:
        with st.form("form_trans"):
            c1, c2, c3 = st.columns(3)
            f_data = c1.date_input("Data")
            f_tipo = c2.selectbox("Tipo", ["Despesa", "Receita"])
            f_nat = c3.selectbox("Natureza", ["Essencial", "Estilo de Vida", "Renda Extra"])
            c4, c5, c6 = st.columns(3)
            f_val = c4.number_input("Valor BRL", min_value=0.0)
            f_cat = c5.selectbox("Categoria", ["Habitação", "Alimentação", "Transporte", "Lazer", "Saúde", "Educação", "Assinaturas", "Outros"])
            f_desc = c6.text_input("Descrição")
            if st.form_submit_button("Confirmar Lançamento"):
                nova_t = Transacao(data=f_data, mes_ano=f_data.strftime("%m/%Y"), descricao=f_desc, 
                                   categoria=f_cat, tipo=f_tipo, natureza=f_nat, valor=f_val)
                session.add(nova_t)
                session.commit()
                st.rerun()

    st.divider()
    items = session.query(Transacao).filter(Transacao.mes_ano == ref).order_by(Transacao.data.desc()).all()
    if items:
        df_view = pd.DataFrame([vars(i) for i in items]).drop('_sa_instance_state', axis=1)
        st.dataframe(df_view, use_container_width=True, hide_index=True)

# ==========================================
# 3. METAS & ENVELOPES
# ==========================================
elif menu == "Metas & Envelope":
    st.title("📦 Caixas e Metas Financeiras")
    with st.expander("➕ Criar Novo Envelope"):
        with st.form("form_meta"):
            c1, c2 = st.columns([1, 4])
            m_icon = c1.text_input("Emoji", value="✈️")
            m_nome = c2.text_input("Nome da Meta")
            c3, c4 = st.columns(2)
            m_alvo = c3.number_input("Valor Necessário (R$)", min_value=1.0)
            m_prazo = c4.date_input("Até quando?")
            if st.form_submit_button("Registrar Meta"):
                nova_meta = MetaFinanceira(nome=m_nome, valor_alvo=m_alvo, prazo=m_prazo, icone=m_icon)
                session.add(nova_meta)
                session.commit()
                st.rerun()

    metas = session.query(MetaFinanceira).all()
    if metas:
        cols = st.columns(3)
        for idx, m in enumerate(metas):
            with cols[idx % 3]:
                with st.container(border=True):
                    st.subheader(f"{m.icone} {m.nome}")
                    progresso = min(m.valor_atual / m.valor_alvo, 1.0) if m.valor_alvo > 0 else 0
                    st.progress(progresso)
                    st.markdown(f"**R$ {m.valor_atual:,.2f}** / {m.valor_alvo:,.2f}")
                    aporte = st.number_input("Aportar:", min_value=0.0, key=f"val_{m.id}")
                    if st.button("Guardar", key=f"btn_{m.id}") and aporte > 0:
                        m.valor_atual += aporte
                        session.commit()
                        st.rerun()

# ==========================================
# 4. SMART REBALANCE
# ==========================================
elif menu == "Smart Rebalance":
    st.title("⚖️ Custódia e Balanceamento")
    with st.expander("💼 Lançar/Atualizar Ativo"):
        with st.form("form_ativo"):
            a1, a2, a3 = st.columns(3)
            a_tick = a1.text_input("Ticker (Ex: WEGE3, AAPL)")
            a_cl = a2.selectbox("Classe", ["Ações BR", "FIIs", "Ações US", "Renda Fixa", "Crypto"])
            a_qtd = a3.number_input("Qtd Atual", min_value=0.0, format="%.4f")
            a4, a5 = st.columns(2)
            a_pm = a4.number_input("Preço Médio (BRL)", min_value=0.0)
            a_yield = a5.number_input("Yield Anual (%)", min_value=0.0)
            if st.form_submit_button("Atualizar Custódia"):
                existente = session.query(Ativo).filter(Ativo.ticker == a_tick.upper()).first()
                if existente:
                    existente.quantidade, existente.preco_medio = a_qtd, a_pm
                else:
                    novo_a = Ativo(ticker=a_tick.upper(), classe=a_cl, quantidade=a_qtd, preco_medio=a_pm, yield_anual=a_yield)
                    session.add(novo_a)
                session.commit()
                st.rerun()

    ativos = session.query(Ativo).all()
    if ativos:
        df_a = pd.DataFrame([vars(a) for a in ativos]).drop('_sa_instance_state', axis=1)
        precos = eng.fetch_prices(df_a['ticker'].unique().tolist())
        usd = eng.get_usd()
        df_a['preco_atual'] = df_a['ticker'].map(precos)
        df_a['cambio'] = df_a['classe'].apply(lambda x: usd if x == 'Ações US' else 1.0)
        df_a['total_atual_brl'] = df_a['quantidade'] * df_a['preco_atual'] * df_a['cambio']
        total_port = df_a['total_atual_brl'].sum()
        resumo = df_a.groupby('classe')['total_atual_brl'].sum().reset_index()
        resumo['atual_%'] = (resumo['total_atual_brl'] / total_port) * 100
        metas = {"Ações BR": user.meta_acoes, "FIIs": user.meta_fiis, "Renda Fixa": user.meta_rf, "Crypto": user.meta_crypto, "Ações US": user.meta_acoes_us}
        resumo['meta_%'] = resumo['classe'].map(metas)
        resumo['desvio_%'] = resumo['atual_%'] - resumo['meta_%']
        st.subheader(f"Patrimônio Global: R$ {total_port:,.2f}")
        st.dataframe(resumo, use_container_width=True, hide_index=True)
        for _, row in resumo.iterrows():
            if row['desvio_%'] < -2: st.info(f"🟢 Comprar {row['classe']} ({abs(row['desvio_%']):.1f}% abaixo)")

# ==========================================
# 5. SIMULADOR FIRE
# ==========================================
elif menu == "Simulador FIRE":
    st.title("🚀 Monte Carlo: Rumo à Independência")
    ativos = session.query(Ativo).all()
    pat_base = sum([a.quantidade * a.preco_medio for a in ativos])
    c1, c2, c3 = st.columns(3)
    ret_anual = c1.slider("Retorno Anual (%)", 5.0, 20.0, 10.0) / 100
    inf_anual = c2.slider("Inflação Anual (%)", 2.0, 15.0, 4.5) / 100
    vol_anual = c3.slider("Volatilidade (%)", 5.0, 30.0, 15.0) / 100
    p_ini = st.number_input("Patrimônio Inicial BRL", value=float(pat_base))
    p_apo = st.number_input("Aporte Mensal BRL", value=2000.0)
    p_gas = st.number_input("Renda Desejada Aposentadoria", value=5000.0)
    anos = st.slider("Horizonte (Anos)", 10, 50, 30)
    if st.button("Simular Cenários", type="primary"):
        trajetorias = eng.monte_carlo_fire(p_ini, p_apo, p_gas, anos, ret_anual, inf_anual, vol_anual)
        fig = go.Figure()
        for t in trajetorias: fig.add_trace(go.Scatter(y=t, mode='lines', line=dict(width=1), opacity=0.1, showlegend=False))
        fig.add_trace(go.Scatter(y=np.median(trajetorias, axis=0), mode='lines', line=dict(color='#00c04b', width=3), name='Mediana'))
        st.plotly_chart(fig, use_container_width=True)

# ==========================================
# 6. CONFIGURAÇÕES
# ==========================================
elif menu == "⚙️ Configurações":
    st.title("⚙️ Setup do Usuário")
    with st.form("cfg_form"):
        user.valor_hora = st.number_input("Valor da Hora", value=user.valor_hora)
        user.horas_dia = st.number_input("Horas/Dia", value=user.horas_dia)
        user.reserva_meses = st.number_input("Meses Reserva", value=user.reserva_meses)
        st.subheader("Metas de Alocação (%)")
        m1, m2, m3, m4, m5 = st.columns(5)
        user.meta_acoes = m1.number_input("Ações BR", value=user.meta_acoes)
        user.meta_fiis = m2.number_input("FIIs", value=user.meta_fiis)
        user.meta_rf = m3.number_input("Renda Fixa", value=user.meta_rf)
        user.meta_acoes_us = m4.number_input("Ações US", value=user.meta_acoes_us)
        user.meta_crypto = m5.number_input("Crypto", value=user.meta_crypto)
        if st.form_submit_button("Salvar"):
            session.commit(); st.success("Salvo!")

session.close()