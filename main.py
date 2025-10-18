import streamlit as st
import pandas as pd
from datetime import datetime, date, timedelta
from pathlib import Path
import altair as alt

# =========================
# Configuração da Página
# =========================
st.set_page_config(page_title="Oi, Zinees", page_icon="💖", layout="wide")

# --- Cabeçalho com título à esquerda e imagem à direita ---
left, right = st.columns([4, 1])

with left:
    st.text("Oi, Zines!")
    st.title("Este é um aplicativo feito com muito carinho para você! 💖")

with right:
    st.image("LOGO.jpeg", width=200)  # troque por caminho/URL da sua imagem

# =========================
# Arquivos / Constantes
# =========================
CSV_PATH  = Path("plantao_template.csv")   # lançamentos
LOCS_PATH = Path("locais.csv")             # cadastro de locais

COLS = [
    "id","data","inicio","fim","duracao_horas","tipo_unidade","especialidade",
    "vinculo","local_nome",
    "valor_bruto","adicionais",
    "custo_deslocamento_ida","custo_deslocamento_volta","custo_refeicao","custo_outros",
    "valor_liquido",
    "condicao_pagamento","data_combinada",
    "fatura_numero","recebido","data_recebimento","forma_pagamento","observacoes"
]
LOCS_COLS = ["local_nome","cidade","uf"]

NUMERIC_COLS = [
    "valor_bruto","adicionais","custo_deslocamento_ida","custo_deslocamento_volta",
    "custo_refeicao","custo_outros","valor_liquido","duracao_horas"
]

TIPO_UNIDADE   = ["Hospitalar","UPA / SAMU","Ambulatorial","Home Care","Telemedicina","Empresarial"]
VINCULOS       = ["CLT","PJ","Autônomo (RPA)","Cooperado","Voluntário"]
PAGAMENTOS     = ["PIX","TED","Dinheiro","Cooperativa","Folha","Outro"]
ESPECIALIDADES = ["Porta","Observação","Urgência e Emergência","UTI"]
CONDICOES      = ["À vista", "Na data combinada"]

# =========================
# Helpers
# =========================
def ensure_csv(path: Path, cols: list[str]):
    if not path.exists():
        pd.DataFrame(columns=cols).to_csv(path, index=False)

def moeda(x: float) -> str:
    return f"R$ {x:,.2f}".replace(",", "X").replace(".", ",").replace("X",".")

def next_id(df: pd.DataFrame) -> int:
    if "id" not in df.columns or df["id"].eq("").all():
        return 1
    return int(pd.to_numeric(df["id"], errors="coerce").fillna(0).max()) + 1

@st.cache_data
def load_df(path: Path) -> pd.DataFrame:
    ensure_csv(path, COLS)
    df = pd.read_csv(path, dtype=str).fillna("")
    for c in COLS:
        if c not in df.columns:
            df[c] = "" if c not in NUMERIC_COLS and c != "recebido" else 0
    for col in NUMERIC_COLS:
        df[col] = pd.to_numeric(df[col].replace({"": 0}), errors="coerce").fillna(0.0)
    df["data_dt"] = pd.to_datetime(df.get("data", ""), errors="coerce")
    if {"inicio","fim"}.issubset(df.columns):
        t1 = pd.to_datetime(df["inicio"], format="%H:%M", errors="coerce")
        t2 = pd.to_datetime(df["fim"],    format="%H:%M", errors="coerce")
        delta = (t2 - t1).dt.total_seconds() / 3600.0
        delta = delta.where(delta >= 0, delta + 24)
        df["duracao_horas"] = pd.to_numeric(df["duracao_horas"], errors="coerce").fillna(delta.round(2)).fillna(0.0)
    custos = (
        df.get("custo_deslocamento_ida", 0)
        + df.get("custo_deslocamento_volta", 0)
        + df.get("custo_refeicao", 0)
        + df.get("custo_outros", 0)
    )
    df["valor_liquido_calc"] = (df.get("valor_bruto", 0) + df.get("adicionais", 0) - custos).round(2)
    df["valor_liquido"] = pd.to_numeric(df["valor_liquido"], errors="coerce").fillna(df["valor_liquido_calc"])
    df["recebido"] = df.get("recebido","").astype(str).str.lower().isin(["1","true","sim","yes"])
    return df

@st.cache_data
def load_locs(path: Path) -> pd.DataFrame:
    ensure_csv(path, LOCS_COLS)
    df = pd.read_csv(path, dtype=str).fillna("")
    for c in LOCS_COLS:
        if c not in df.columns: df[c] = ""
    return df[LOCS_COLS]

def save_df(df: pd.DataFrame, path: Path) -> None:
    out = df.copy()
    out["recebido"] = out["recebido"].astype(int)
    for c in ["data_dt","valor_liquido_calc"]:
        if c in out.columns: out.drop(columns=c, inplace=True)
    for c in COLS:
        if c not in out.columns:
            out[c] = "" if c not in NUMERIC_COLS and c != "recebido" else 0
    out = out[COLS]
    out.to_csv(path, index=False)

def save_locs(df: pd.DataFrame, path: Path) -> None:
    out = df.copy()
    for c in LOCS_COLS:
        if c not in out.columns: out[c] = ""
    out = out[LOCS_COLS]
    out.to_csv(path, index=False)

# =========================
# Carrega dados
# =========================
df  = load_df(CSV_PATH)
dlc = load_locs(LOCS_PATH)

# =========================
# Tabs
# =========================
tab_dash, tab_crud, tab_locs = st.tabs(["📊 Dashboard","📝 Lançamentos (CRUD)","📍 Locais"])

# ========= DASHBOARD =========
with tab_dash:
    st.subheader("Resumo e Filtros")

    if "data_dt" in df.columns and not df["data_dt"].dropna().empty:
        dmin = df["data_dt"].min().date()
        dmax = df["data_dt"].max().date()
    else:
        dmin = date.today() - timedelta(days=30)
        dmax = date.today()

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        periodo = st.date_input("Período", value=(dmin, dmax))
    with c2:
        sel_tipo = st.multiselect("Tipo de unidade", sorted(df.get("tipo_unidade", pd.Series(dtype=str)).dropna().unique().tolist()))
    with c3:
        sel_vinculo = st.multiselect("Vínculo", sorted(df.get("vinculo", pd.Series(dtype=str)).dropna().unique().tolist()))
    with c4:
        sel_espec = st.multiselect("Especialidade", sorted(df.get("especialidade", pd.Series(dtype=str)).dropna().unique().tolist()))

    filt = pd.Series(True, index=df.index)
    filt &= (df["data_dt"] >= pd.to_datetime(periodo[0])) & (df["data_dt"] <= pd.to_datetime(periodo[1]))
    if sel_tipo:    filt &= df.get("tipo_unidade","").isin(sel_tipo)
    if sel_vinculo: filt &= df.get("vinculo","").isin(sel_vinculo)
    if sel_espec:   filt &= df.get("especialidade","").isin(sel_espec)

    view = df[filt].copy()

    k1,k2,k3,k4 = st.columns(4)
    with k1: st.metric("Plantões", len(view))
    with k2: st.metric("Horas", round(view.get("duracao_horas", pd.Series([0])).sum(), 2))
    with k3: st.metric("Bruto",  moeda(view.get("valor_bruto",  pd.Series([0])).sum()))
    with k4: st.metric("Líquido",moeda(view.get("valor_liquido",pd.Series([0])).sum()))

    st.divider()
    st.subheader("Lançamentos filtrados")
    st.dataframe(view.drop(columns=[c for c in ["data_dt","valor_liquido_calc"] if c in view.columns]), use_container_width=True)

    st.divider()
    st.subheader("Gráficos")

    if view.empty or "data_dt" not in view.columns or view["data_dt"].dropna().empty:
        st.info("Sem dados para os gráficos neste período/combinação de filtros.")
    else:
        monthly = (
            view.dropna(subset=["data_dt"])
                .assign(mes=lambda x: x["data_dt"].dt.to_period("M").dt.to_timestamp())
                .groupby("mes", as_index=False)["valor_liquido"].sum()
        )
        chart1 = (
            alt.Chart(monthly)
               .mark_line(point=True)
               .encode(x="mes:T", y="valor_liquido:Q", tooltip=["mes","valor_liquido"])
               .properties(height=300)
        )
        st.altair_chart(chart1, use_container_width=True)

        cA, cB = st.columns(2)

        with cA:
            if "vinculo" in view.columns:
                by_v = (view.groupby("vinculo", as_index=False)["valor_liquido"]
                             .sum().sort_values("valor_liquido", ascending=False))
                st.altair_chart(
                    alt.Chart(by_v).mark_bar().encode(
                        x=alt.X("vinculo:N", sort="-y"),
                        y="valor_liquido:Q",
                        tooltip=["vinculo","valor_liquido"]
                    ).properties(height=300),
                    use_container_width=True
                )

        with cB:
            if "tipo_unidade" in view.columns:
                by_t = (view.groupby("tipo_unidade", as_index=False)["valor_liquido"]
                             .sum().sort_values("valor_liquido", ascending=False))
                st.altair_chart(
                    alt.Chart(by_t).mark_bar().encode(
                        x=alt.X("tipo_unidade:N", sort="-y"),
                        y="valor_liquido:Q",
                        tooltip=["tipo_unidade","valor_liquido"]
                    ).properties(height=300),
                    use_container_width=True
                )


# ========= CRUD =========
with tab_crud:
    st.subheader("Adicionar novo plantão")

    loc_options = sorted(dlc["local_nome"].dropna().unique().tolist())
    if not loc_options:
        st.warning("Nenhum **Local do plantão** cadastrado. Adicione na aba **📍 Locais**.")

    with st.form("novo_plantao"):
        # Linha 1: Data | Local do plantão | Início | Fim
        c1, c2, c3, c4 = st.columns([1.1, 1.8, 1.0, 1.0])

        with c1:
            data_new = st.date_input("Data", value=date.today())

        with c2:
            local_nome_new = st.selectbox(
                "Local do plantão",
                loc_options if loc_options else ["— cadastre na aba Locais —"],
                index=0,
                disabled=(len(loc_options) == 0),
                key="local_nome_select",
            )

        # defaults redondos e independentes
        default_ini_dt = datetime.now().replace(minute=0, second=0, microsecond=0)
        default_ini = default_ini_dt.time()

        with c3:
            inicio_new = st.time_input("Início", value=default_ini, key="inicio_time")

        with c4:
            # fim padrão = início + 12h (recalcula conforme o início atual)
            fim_default = (datetime.combine(date.today(), inicio_new) + timedelta(hours=12)).time()
            fim_new = st.time_input("Fim", value=fim_default, key="fim_time")

        # Linha 2: Tipo de unidade | Vínculo | Especialidade
        c5,c6,c7 = st.columns([1.4,1.2,1.6])
        with c5: tipo_unidade_new = st.selectbox("Tipo de unidade", TIPO_UNIDADE, index=0)
        with c6: vinculo_new      = st.selectbox("Vínculo", VINCULOS, index=1)
        with c7: especialidade_new= st.selectbox("Especialidade", ESPECIALIDADES, index=0)

        # Linha 3: Valores
        c8,c9 = st.columns(2)
        with c8: valor_bruto_new  = st.number_input("Valor", min_value=0.0, step=50.0, format="%.2f")
        with c9: adicionais_new   = st.number_input("Adicionais", min_value=0.0, step=10.0, format="%.2f")

        # Linha 4: Custos (ida/volta)
        c10,c11,c12,c13 = st.columns(4)
        with c10: desloc_ida_new   = st.number_input("Custo deslocamento (ida)",   min_value=0.0, step=5.0, format="%.2f")
        with c11: desloc_volta_new = st.number_input("Custo deslocamento (volta)", min_value=0.0, step=5.0, format="%.2f")
        with c12: refei_new        = st.number_input("Custo refeição",             min_value=0.0, step=5.0, format="%.2f")
        with c13: outros_new       = st.number_input("Outros custos",               min_value=0.0, step=5.0, format="%.2f")

        # Linha 5: Condição de pagamento + Data combinada ao lado
        c14, c15 = st.columns([1.2, 1.0])
        with c14:
            condicao_new = st.radio("Condição de pagamento", CONDICOES, index=0, horizontal=True, key="condicao_radio")
        with c15:
            data_combinada_enabled = (condicao_new == "Na data combinada")
            data_combinada_new = st.date_input(
                "Data combinada",
                value=(data_new + timedelta(days=30)) if data_combinada_enabled else None,
                disabled=not data_combinada_enabled,
                key="data_combinada_input"
            )

        # Linha 6: Forma de pagamento
        c16 = st.columns(1)[0]
        with c16:
            forma_new = st.selectbox("Forma de pagamento", PAGAMENTOS, index=0)

        # Linha 7: Recebimento efetivo (pode ajustar)
        c17, c18 = st.columns(2)
        with c17:
            recebido_new = st.checkbox("Recebido?", value=False)
        with c18:
            data_recebimento_default = data_combinada_new if data_combinada_enabled and data_combinada_new else data_new
            data_rec_new = st.date_input("Data recebimento", value=data_recebimento_default, disabled=not recebido_new)

        obs_new = st.text_area("Observações", value="")

        submitted = st.form_submit_button("Adicionar", disabled=(len(loc_options)==0))
        if submitted:
            # duração considera a data escolhida
            t1 = datetime.combine(data_new, inicio_new)
            t2 = datetime.combine(data_new, fim_new)
            dur = (t2 - t1).total_seconds()/3600
            if dur < 0: dur += 24

            custos = desloc_ida_new + desloc_volta_new + refei_new + outros_new
            liquido = (valor_bruto_new + adicionais_new) - custos

            new_row = {
                "id": next_id(df),
                "data": data_new.strftime("%Y-%m-%d"),
                "inicio": inicio_new.strftime("%H:%M"),
                "fim": fim_new.strftime("%H:%M"),
                "duracao_horas": round(dur,2),
                "tipo_unidade": tipo_unidade_new,
                "especialidade": especialidade_new,
                "vinculo": vinculo_new,
                "local_nome": local_nome_new if loc_options else "",
                "valor_bruto": round(valor_bruto_new,2),
                "adicionais": round(adicionais_new,2),
                "custo_deslocamento_ida": round(desloc_ida_new,2),
                "custo_deslocamento_volta": round(desloc_volta_new,2),
                "custo_refeicao": round(refei_new,2),
                "custo_outros": round(outros_new,2),
                "valor_liquido": round(liquido,2),
                "condicao_pagamento": condicao_new,
                "data_combinada": data_combinada_new.strftime("%Y-%m-%d") if data_combinada_new else "",
                "fatura_numero": "",
                "recebido": bool(recebido_new),
                "data_recebimento": data_rec_new.strftime("%Y-%m-%d") if (recebido_new and data_rec_new) else "",
                "forma_pagamento": forma_new,
                "observacoes": obs_new,
            }
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
            save_df(df, CSV_PATH)
            st.success("Plantão adicionado!")
            st.cache_data.clear()

    st.divider()
    st.subheader("Editar/Excluir lançamentos")
    edited = st.data_editor(
        df.drop(columns=[c for c in ["data_dt","valor_liquido_calc"] if c in df.columns]),
        use_container_width=True,
        num_rows="dynamic",
        column_config={
            "tipo_unidade":  st.column_config.SelectboxColumn("Tipo de unidade", options=TIPO_UNIDADE),
            "especialidade": st.column_config.SelectboxColumn("Especialidade",  options=ESPECIALIDADES),
            "condicao_pagamento": st.column_config.SelectboxColumn("Condição de pagamento", options=CONDICOES),
            "recebido":      st.column_config.CheckboxColumn("Recebido?"),
        },
        key="editor_lanc",
    )
    if st.button("💾 Salvar alterações no CSV", use_container_width=True):
        save_df(edited, CSV_PATH)
        st.success("Atualizado com sucesso!")
        st.cache_data.clear()

# ========= 📍 LOCAIS =========
with tab_locs:
    st.subheader("Cadastro de Locais do plantão")

    with st.form("novo_local"):
        lc1, lc2, lc3 = st.columns([2, 1, 0.6])
        with lc1: nome   = st.text_input("Local do plantão (nome)", placeholder="Ex.: Hospital Municipal Doutor Alexandre Zaio")
        with lc2: cidade = st.text_input("Cidade", placeholder="Ex.: São Paulo")
        with lc3: uf     = st.text_input("UF", max_chars=2, placeholder="SP")
        if st.form_submit_button("Adicionar local"):
            if not nome.strip():
                st.error("Informe o nome do **Local do plantão**.")
            else:
                novo = {"local_nome": nome.strip(), "cidade": cidade.strip(), "uf": uf.strip().upper()}
                dlc = pd.concat([dlc, pd.DataFrame([novo])], ignore_index=True)
                save_locs(dlc, LOCS_PATH)
                st.success("Local cadastrado!")
                st.cache_data.clear()

    st.divider()
    st.subheader("Editar/Excluir locais")
    dlc_edit = st.data_editor(
        load_locs(LOCS_PATH),
        use_container_width=True,
        num_rows="dynamic",
        key="editor_locs",
        column_config={
            "local_nome": st.column_config.TextColumn("Local do plantão"),
            "cidade":     st.column_config.TextColumn("Cidade"),
            "uf":         st.column_config.TextColumn("UF"),
        },
    )
    if st.button("💾 Salvar alterações nos locais", use_container_width=True):
        save_locs(dlc_edit, LOCS_PATH)
        st.success("Locais atualizados!")
        st.cache_data.clear()