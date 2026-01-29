import streamlit as st
import pandas as pd
import psycopg2
import io
import time
import smtplib
import re
import base64
from email.message import EmailMessage
from datetime import date, datetime, timedelta
import os 

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Georgia Luft - Sistema Jurídico", layout="wide", page_icon="⚖️", initial_sidebar_state="expanded")

# --- CONFIGURAÇÕES DO EMAIL (BLINDAGEM TOTAL VIA SECRETS) ---
try:
    # Busca tudo no cofre. Se não achar, define vazio para não quebrar o app na inicialização
    EMAIL_REMETENTE = st.secrets["EMAIL_REMETENTE"]
    SENHA_DO_EMAIL = st.secrets["EMAIL_SENHA"]
    EMAIL_DESTINATARIO = st.secrets["EMAIL_DESTINATARIO"]
except:
    EMAIL_REMETENTE = ""
    SENHA_DO_EMAIL = ""
    EMAIL_DESTINATARIO = ""

# ==============================================================================
# 🔐 SISTEMA DE LOGIN
# ==============================================================================
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return None

def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if not st.session_state["password_correct"]:
        # --- CSS LOGIN (Esconde Sidebar) ---
        st.markdown("""
        <style>
            .stApp { background-color: #151A1E !important; }
            [data-testid="stSidebar"] { display: none !important; }
            [data-testid="stSidebarCollapsedControl"] { display: none !important; }
            .login-title { font-family: 'Cinzel', serif; color: #C5A065; text-align: center; font-size: 32px; margin-bottom: 5px; }
            .login-subtitle { font-family: 'Lato', sans-serif; color: #FFFFFF; text-align: center; font-size: 14px; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 30px; }
            .stTextInput input { background-color: #FFFFFF !important; color: #000000 !important; border: 2px solid #C5A065 !important; }
            .stButton button { background-color: #C5A065 !important; color: #000000 !important; font-weight: bold; width: 100%; }
        </style>
        """, unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.markdown("<br><br>", unsafe_allow_html=True)
            img_b64 = get_base64_image("foto_georgia.jpg")
            if img_b64:
                st.markdown(f"""<div style="display:flex;justify-content:center;margin-bottom:15px;"><img src="data:image/jpeg;base64,{img_b64}" style="width:120px;height:120px;border-radius:50%;border:3px solid #C5A065;object-fit:cover;"></div>""", unsafe_allow_html=True)
            
            st.markdown('<div class="login-title">GEORGIA LUFT</div>', unsafe_allow_html=True)
            st.markdown('<div class="login-subtitle">Sistema Jurídico Integrado</div>', unsafe_allow_html=True)
            
            with st.form("login_form"):
                senha_digitada = st.text_input("Credencial", type="password", placeholder="Digite sua senha...")
                submitted = st.form_submit_button("ACESSAR")
            
            if submitted:
                if "SENHA_DO_SISTEMA" in st.secrets:
                    if senha_digitada == st.secrets["SENHA_DO_SISTEMA"]:
                        st.session_state["password_correct"] = True
                        st.rerun()
                    else:
                        st.error("🚫 Senha incorreta.")
                else:
                    st.error("⚠️ ERRO: Configure a senha nos Secrets.")
        return False
    else:
        return True

if not check_password():
    st.stop()

# ==============================================================================
# 🚀 APLICAÇÃO PRINCIPAL
# ==============================================================================

# --- CSS GERAL (Restaura Sidebar) ---
st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Lato:wght@300;400;700&family=Cinzel:wght@700&display=swap');
        [data-testid="stSidebar"] { display: block !important; visibility: visible !important; background-color: #151A1E !important; }
        [data-testid="stSidebarCollapsedControl"] { display: block !important; visibility: visible !important; color: #000000 !important; }
        [data-testid="stAppViewContainer"] { background-color: #F4F6F9 !important; color: #000000 !important; }
        h1, h2, h3, p, li, span, div, label { color: #1E252B !important; }
        [data-testid="stSidebar"] h1, [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] div, [data-testid="stSidebar"] label { color: #FFFFFF !important; }
        .main-card, div[data-testid="stMetric"] { background-color: #FFFFFF !important; padding: 20px; border-radius: 12px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); border: 1px solid #E0E0E0; margin-bottom: 15px; }
        div[data-testid="stMetric"] { border-left: 5px solid #C5A065; }
        .stButton button { background-color: #151A1E !important; color: #FFFFFF !important; border-radius: 6px; font-weight: 600; border: none; }
        .stButton button:hover { background-color: #C5A065 !important; color: #000000 !important; }
        div.btn-alerta button { background-color: #D32F2F !important; color: white !important; }
        div.btn-alerta button:hover { background-color: #B71C1C !important; }
        [data-testid="stSidebar"] .stRadio label p { color: #FFFFFF !important; font-size: 16px !important; }
        #MainMenu {visibility: hidden;} footer {visibility: hidden;} header {background-color: transparent !important;}
    </style>
""", unsafe_allow_html=True)

# --- CONEXÃO E BANCO ---
@st.cache_resource
def init_connection():
    try: return psycopg2.connect(st.secrets["DATABASE_URL"])
    except: return None

def conectar_banco():
    conn = init_connection()
    if conn and conn.closed: st.cache_resource.clear(); conn = init_connection()
    return conn

def limpar_cache_dados(): st.cache_data.clear()

def criar_tabelas():
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor:
            cursor.execute('''CREATE TABLE IF NOT EXISTS prazos (id SERIAL PRIMARY KEY, numero_processo TEXT, nome_cliente TEXT, info TEXT, evento TEXT, data_prazo DATE, obs TEXT, status TEXT DEFAULT 'Pendente')''')
            cursor.execute('''CREATE TABLE IF NOT EXISTS atendimentos (id SERIAL PRIMARY KEY, data_atendimento DATE, nome_cliente TEXT, cpf_cliente TEXT, telefone TEXT, senha_sigrh TEXT, motivo TEXT, obs TEXT)''')
        conn.commit()

# --- CRUD ---
def adicionar_prazo(numero, nome, info, evento, data, obs):
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor: cursor.execute("INSERT INTO prazos (numero_processo, nome_cliente, info, evento, data_prazo, obs, status) VALUES (%s, %s, %s, %s, %s, %s, 'Pendente')", (numero, nome, info, evento, data, obs))
        conn.commit(); limpar_cache_dados() 

def adicionar_atendimento(data, nome, cpf, telefone, senha, motivo):
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor: cursor.execute("INSERT INTO atendimentos (data_atendimento, nome_cliente, cpf_cliente, telefone, senha_sigrh, motivo, obs) VALUES (%s, %s, %s, %s, %s, %s, '')", (data, nome, cpf, telefone, senha, motivo))
        conn.commit(); limpar_cache_dados()

@st.cache_data(ttl=600) 
def carregar_dados(tabela, status_filtro=None):
    conn = conectar_banco()
    df = pd.DataFrame()
    if conn:
        try:
            if tabela == 'prazos':
                query = "SELECT * FROM prazos WHERE status = %s"
                df = pd.read_sql(query, conn, params=(status_filtro,))
                if not df.empty:
                    df['data_prazo'] = pd.to_datetime(df['data_prazo']).dt.date
                    df = df.sort_values(by='data_prazo', ascending=(status_filtro == 'Pendente'))
            else:
                query = "SELECT * FROM atendimentos"
                df = pd.read_sql(query, conn)
                if not df.empty:
                    df['data_atendimento'] = pd.to_datetime(df['data_atendimento']).dt.date
                    df = df.sort_values(by='data_atendimento', ascending=False)
        except: pass
    return df

def atualizar_registro(tabela, id_reg, dados):
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor:
            sets = ", ".join([f"{col} = %s" for col in dados.keys()])
            valores = list(dados.values()); valores.append(id_reg)
            cursor.execute(f"UPDATE {tabela} SET {sets} WHERE id = %s", valores)
        conn.commit(); limpar_cache_dados()

def excluir_registro_db(tabela, lista_ids):
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor: cursor.executemany(f"DELETE FROM {tabela} WHERE id = %s", [(i,) for i in lista_ids])
        conn.commit(); limpar_cache_dados()

def alterar_status_lote(lista_ids, novo_status):
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor: cursor.executemany("UPDATE prazos SET status = %s WHERE id = %s", [(novo_status, i) for i in lista_ids])
        conn.commit(); limpar_cache_dados()

def resetar_tabela_prazos():
    conn = conectar_banco()
    if conn:
        with conn.cursor() as cursor: cursor.execute("DELETE FROM prazos")
        conn.commit(); limpar_cache_dados()

def enviar_email_alerta(df_urgente):
    if not EMAIL_REMETENTE or not SENHA_DO_EMAIL or not EMAIL_DESTINATARIO:
        st.error("Erro: Credenciais de e-mail incompletas nos Secrets!")
        return
    
    msg = EmailMessage()
    msg['Subject'] = f"🚨 URGENTE: {len(df_urgente)} Processos Vencendo!"
    msg['From'] = EMAIL_REMETENTE
    msg['To'] = EMAIL_DESTINATARIO
    
    corpo = "Olá Dra. Georgia,\n\nOs seguintes processos precisam de atenção IMEDIATA:\n\n"
    for _, row in df_urgente.iterrows():
        d = row['data_prazo'].strftime('%d/%m/%Y')
        corpo += f"🔴 {d} - {row['nome_cliente']} (Proc: {row['numero_processo']})\n   Evento: {row['evento']}\n\n"
    
    corpo += "\nAcesse o sistema: https://share.streamlit.io"
    msg.set_content(corpo)

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
            smtp.login(EMAIL_REMETENTE, SENHA_DO_EMAIL)
            smtp.send_message(msg)
        st.toast("✅ E-mail enviado com sucesso!")
    except Exception as e:
        st.error(f"Falha ao enviar e-mail: {e}")

criar_tabelas()

def calcular_urgencia(data_prazo):
    if not isinstance(data_prazo, date): return "⚪"
    hoje = date.today(); dias = (data_prazo - hoje).days
    if dias < 0: return "🔴 ATRASADO"
    elif dias == 0: return "🚨 HOJE"
    elif dias <= 3: return "🔥 URGENTE"
    else: return "✅ NO PRAZO"

def verificar_edicoes(df_original, df_editado, tabela):
    if tabela == 'prazos': cols = ['numero_processo', 'nome_cliente', 'info', 'evento', 'data_prazo', 'obs']
    else: cols = ['data_atendimento', 'nome_cliente', 'cpf_cliente', 'telefone', 'senha_sigrh', 'motivo', 'obs']
    ids_na_tela = df_editado['id'].tolist()
    df_orig_filtrada = df_original[df_original['id'].isin(ids_na_tela)].set_index('id')[cols]
    df_new = df_editado.set_index('id')[cols]
    diff = df_orig_filtrada.astype(str).compare(df_new.astype(str))
    if not diff.empty:
        for id_alt in diff.index.unique():
            linha = df_new.loc[id_alt]
            dados = {c: linha[c] for c in cols}
            atualizar_registro(tabela, int(id_alt), dados)
        return True
    return False

# --- SIDEBAR FIXO ---
with st.sidebar:
    img_b64 = get_base64_image("foto_georgia.jpg")
    if img_b64: st.markdown(f"""<div style="text-align:center;margin-bottom:20px;border-bottom:1px solid #444;padding-bottom:20px;"><img src="data:image/jpeg;base64,{img_b64}" style="width:100px;height:100px;border-radius:50%;border:3px solid #C5A065;object-fit:cover;"/><div style="color:white;font-family:'Cinzel';font-size:16px;margin-top:10px;">Dra. Georgia Luft</div><div style="color:#C5A065;font-size:11px;letter-spacing:2px;text-transform:uppercase;">Advogada</div></div>""", unsafe_allow_html=True)
    menu_selecionado = st.radio("NAVEGAÇÃO", ["📊 Dashboard (Prazos)", "👥 Atendimentos", "📂 Arquivo Morto", "📥 Importação Excel"], label_visibility="collapsed")
    st.markdown("---")
    st.markdown(f"<div style='text-align: center; color: white !important;'>📅 {date.today().strftime('%d/%m/%Y')}</div>", unsafe_allow_html=True)
    if st.button("Sair / Logout"): st.session_state["password_correct"] = False; st.rerun()

# --- ÁREA PRINCIPAL ---
df_prazos = carregar_dados('prazos', 'Pendente')
df_atend = carregar_dados('atendimentos')
hoje = date.today()

if "Dashboard" in menu_selecionado:
    st.title("Painel de Controle")
    st.markdown("Visão geral dos prazos processuais e urgências.")
    qtd_hoje = len(df_prazos[df_prazos['data_prazo'] == hoje]) if not df_prazos.empty else 0
    data_7_dias = hoje + timedelta(days=7)
    qtd_7_dias = len(df_prazos[(df_prazos['data_prazo'] > hoje) & (df_prazos['data_prazo'] <= data_7_dias)]) if not df_prazos.empty else 0
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Vencendo Hoje", qtd_hoje); k2.metric("Próximos 7 Dias", qtd_7_dias); k3.metric("Total na Fila", len(df_prazos)); k4.metric("Atendimentos", len(df_atend))
    st.write("")
    if not df_prazos.empty:
        df_prazos['STATUS'] = df_prazos['data_prazo'].apply(calcular_urgencia)
        df_prazos['CONCLUÍDO'] = False; df_prazos['EXCLUIR'] = False
        df_urgente = df_prazos[df_prazos['data_prazo'] <= hoje].copy()
        df_futuro = df_prazos[df_prazos['data_prazo'] > hoje].copy()
        if not df_urgente.empty:
            st.markdown("""<div class="main-card" style="border-left: 5px solid #D32F2F;"><h3 style="color: #D32F2F; margin:0;">🔥 AÇÃO NECESSÁRIA</h3><p style="color: #555;">Processos vencendo hoje ou atrasados.</p>""", unsafe_allow_html=True)
            st.markdown('<div class="btn-alerta">', unsafe_allow_html=True)
            if st.button("🔔 DISPARAR ALERTA DE EMAIL"): 
                enviar_email_alerta(df_urgente)
            st.markdown('</div>', unsafe_allow_html=True)
            editor_urg = st.data_editor(df_urgente[['CONCLUÍDO', 'STATUS', 'data_prazo', 'nome_cliente', 'numero_processo', 'info', 'evento', 'obs', 'EXCLUIR', 'id']], column_config={"CONCLUÍDO": st.column_config.CheckboxColumn("Baixar", width="small"), "STATUS": st.column_config.TextColumn("Status", width="small"), "data_prazo": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"), "nome_cliente": st.column_config.TextColumn("Cliente", width="medium"), "EXCLUIR": st.column_config.CheckboxColumn("Del", width="small"), "id": None}, hide_index=True, use_container_width=True, key="grid_urg")
            st.markdown("</div>", unsafe_allow_html=True)
            if verificar_edicoes(df_prazos, editor_urg, 'prazos'): st.toast("Salvo!"); time.sleep(0.5); st.rerun()
            if editor_urg[editor_urg['EXCLUIR']].any().any(): excluir_registro_db('prazos', editor_urg[editor_urg['EXCLUIR']]['id'].tolist()); st.rerun()
            if editor_urg[editor_urg['CONCLUÍDO']].any().any(): alterar_status_lote(editor_urg[editor_urg['CONCLUÍDO']]['id'].tolist(), 'Concluído'); st.rerun()
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("📅 Próximos Prazos")
        if not df_futuro.empty:
            editor_fut = st.data_editor(df_futuro[['CONCLUÍDO', 'STATUS', 'data_prazo', 'nome_cliente', 'numero_processo', 'info', 'evento', 'obs', 'EXCLUIR', 'id']], column_config={"CONCLUÍDO": st.column_config.CheckboxColumn("Baixar"), "STATUS": st.column_config.TextColumn("Status"), "data_prazo": st.column_config.DateColumn("Vencimento", format="DD/MM/YYYY"), "nome_cliente": st.column_config.TextColumn("Cliente", width="medium"), "EXCLUIR": st.column_config.CheckboxColumn("Del"), "id": None}, hide_index=True, use_container_width=True, key="grid_fut")
            if verificar_edicoes(df_prazos, editor_fut, 'prazos'): st.toast("Salvo!"); time.sleep(0.5); st.rerun()
            if editor_fut[editor_fut['EXCLUIR']].any().any(): excluir_registro_db('prazos', editor_fut[editor_fut['EXCLUIR']]['id'].tolist()); st.rerun()
            if editor_fut[editor_fut['CONCLUÍDO']].any().any(): alterar_status_lote(editor_fut[editor_fut['CONCLUÍDO']]['id'].tolist(), 'Concluído'); st.rerun()
        else: st.info("Agenda futura livre.")
        st.markdown('</div>', unsafe_allow_html=True)
    else: st.success("Tudo em dia! Nenhuma pendência.")

elif "Atendimentos" in menu_selecionado:
    st.title("Gestão de Clientes")
    col1, col2 = st.columns([1,1])
    with col1:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("📝 Novo Atendimento"); 
        with st.form("form_atend"):
            f_data = st.date_input("Data", date.today()); f_nome = st.text_input("Nome"); c_cpf, c_tel = st.columns(2); f_cpf = c_cpf.text_input("CPF"); f_tel = c_tel.text_input("Telefone"); f_senha = st.text_input("Senha SIGRH"); f_motivo = st.text_area("Motivo")
            if st.form_submit_button("Salvar Ficha"): adicionar_atendimento(f_data, f_nome, f_cpf, f_tel, f_senha, f_motivo); st.toast("Sucesso!"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="main-card">', unsafe_allow_html=True)
        st.subheader("📄 Importar do Word"); st.info("Cole a lista (Ex: '1. NOME: motivo')"); txt_word = st.text_area("Texto", height=150, label_visibility="collapsed"); dt_imp = st.date_input("Data da lista", date.today())
        if st.button("Processar Lista"):
            count = 0
            if txt_word:
                for linha in txt_word.split('\n'):
                    linha = linha.strip(); 
                    if len(linha) < 5: continue
                    match = re.match(r'^\s*(\d+)[\.\)\-\s]\s*(.+)', linha); conteudo = match.group(2) if match else linha
                    if ":" in conteudo: p = conteudo.split(":", 1); nm = p[0].strip().upper(); mt = p[1].strip()
                    elif "-" in conteudo: p = conteudo.split("-", 1); nm = p[0].strip().upper(); mt = p[1].strip()
                    else: nm = conteudo.upper(); mt = "Verificar anotações"
                    adicionar_atendimento(dt_imp, nm, "", "", "", mt); count += 1
                if count > 0: st.success(f"{count} importados!"); time.sleep(1.5); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.subheader("🔍 Histórico Completo"); busca = st.text_input("Pesquisar", placeholder="Nome, CPF ou Motivo...", label_visibility="collapsed"); df_exibir = df_atend.copy()
    if not df_atend.empty and busca: mask = (df_atend['nome_cliente'].str.contains(busca, case=False, na=False) | df_atend['cpf_cliente'].str.contains(busca, case=False, na=False) | df_atend['motivo'].str.contains(busca, case=False, na=False)); df_exibir = df_atend[mask]
    if not df_exibir.empty:
        df_exibir['EXCLUIR'] = False
        ed_crm = st.data_editor(df_exibir[['data_atendimento', 'nome_cliente', 'cpf_cliente', 'telefone', 'senha_sigrh', 'motivo', 'obs', 'EXCLUIR', 'id']], column_config={"data_atendimento": st.column_config.DateColumn("Data", format="DD/MM/YYYY", width="small"), "nome_cliente": st.column_config.TextColumn("Nome", width="medium"), "motivo": st.column_config.TextColumn("Resumo", width="large"), "EXCLUIR": st.column_config.CheckboxColumn("Del", width="small"), "id": None}, hide_index=True, use_container_width=True, key="grid_crm")
        if verificar_edicoes(df_atend, ed_crm, 'atendimentos'): st.toast("Atualizado!"); time.sleep(0.5)
        if ed_crm[ed_crm['EXCLUIR']].any().any(): excluir_registro_db('atendimentos', ed_crm[ed_crm['EXCLUIR']]['id'].tolist()); st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

elif "Arquivo Morto" in menu_selecionado:
    st.title("Arquivo Morto"); st.markdown('<div class="main-card">', unsafe_allow_html=True)
    df_hist = carregar_dados('prazos', 'Concluído'); busca_morto = st.text_input("Pesquisar no Histórico", placeholder="Nome ou Processo...")
    if not df_hist.empty:
        if busca_morto: mask = (df_hist['nome_cliente'].str.contains(busca_morto, case=False, na=False) | df_hist['numero_processo'].str.contains(busca_morto, case=False, na=False)); df_hist = df_hist[mask]
        if not df_hist.empty:
            df_hist['RESTAURAR'] = False; df_hist['EXCLUIR'] = False
            ed_hist = st.data_editor(df_hist[['RESTAURAR', 'data_prazo', 'nome_cliente', 'numero_processo', 'info', 'EXCLUIR', 'id']], column_config={"RESTAURAR": st.column_config.CheckboxColumn("Restaurar"), "data_prazo": st.column_config.DateColumn("Data", format="DD/MM/YYYY", disabled=True), "EXCLUIR": st.column_config.CheckboxColumn("Del Permanente"), "id": None}, hide_index=True, use_container_width=True, key="grid_hist")
            if ed_hist[ed_hist['EXCLUIR']].any().any(): excluir_registro_db('prazos', ed_hist[ed_hist['EXCLUIR']]['id'].tolist()); st.rerun()
            if ed_hist[ed_hist['RESTAURAR']].any().any(): alterar_status_lote(ed_hist[ed_hist['RESTAURAR']]['id'].tolist(), 'Pendente'); st.rerun()
        else: st.warning("Nada encontrado.")
    else: st.info("Arquivo morto vazio.")
    st.markdown('</div>', unsafe_allow_html=True)

elif "Importação" in menu_selecionado:
    st.title("Importação em Massa"); st.markdown('<div class="main-card">', unsafe_allow_html=True)
    st.info("Copie do Excel e cole abaixo. Formato: Processo | Nome | Info | Evento | Data | Obs")
    with st.form("imp_excel"):
        txt = st.text_area("Dados", height=200)
        if st.form_submit_button("Importar Dados"):
            try:
                if txt:
                    dfi = pd.read_csv(io.StringIO(txt), sep='\t', header=None, dtype=str)
                    count_p = 0
                    for _, r in dfi.iterrows():
                        if pd.isna(r.get(0)): continue
                        proc = r.get(0, "-"); nm = r.get(1, "Sem Nome"); inf = r.get(2, ""); ev = r.get(3, ""); dt_raw = r.get(4, ""); ob = r.get(5, "") if dfi.shape[1]>5 else ""
                        try: d = pd.to_datetime(dt_raw, dayfirst=True).date()
                        except: d = date.today(); ob = f"[ERRO DATA: {dt_raw}] " + str(ob)
                        adicionar_prazo(proc, nm, inf, ev, d, ob); count_p += 1
                    st.success(f"{count_p} prazos importados!"); time.sleep(1); st.rerun()
            except Exception as e: st.error(f"Erro: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("⚠️ Área de Perigo")
    if "confirm_reset" not in st.session_state: st.session_state["confirm_reset"] = False
    if st.button("🗑️ APAGAR TODOS OS PRAZOS (RESET)", type="primary"): st.session_state["confirm_reset"] = True
    if st.session_state["confirm_reset"]:
        st.error("TEM CERTEZA? Isso vai apagar TODOS os prazos do sistema permanentemente.")
        col_sim, col_nao = st.columns(2)
        if col_sim.button("Sim, apagar tudo"):
            resetar_tabela_prazos(); st.success("Banco de dados de prazos resetado!"); st.session_state["confirm_reset"] = False; time.sleep(2); st.rerun()
        if col_nao.button("Cancelar"): st.session_state["confirm_reset"] = False; st.rerun()