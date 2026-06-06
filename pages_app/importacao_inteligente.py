from datetime import date, time, timedelta
import pandas as pd
import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import data_input_br, recarregar
from services.inteligencia_documentos_service import analisar_documento_saude, salvar_importacao_assistida
from services.documentos_service import salvar_documento
from services.exames_service import salvar_exame
from services.medicamentos_service import salvar_medicamento
from services.marcos_service import salvar_marco, listar_marcos_opcoes
from services.pendencias_service import criar_pendencia


def _hora_from_str(txt, default=time(8, 0)):
    try:
        h, m = str(txt).split(":")[:2]
        return time(int(h), int(m))
    except Exception:
        return default


def _nome_usuario(usuario):
    try:
        return usuario.get("nome", "usuário ativo")
    except Exception:
        try:
            return usuario["nome"]
        except Exception:
            return "usuário ativo"


def render_importacao_inteligente(usuario_id, usuario=None):
    nome_ativo = _nome_usuario(usuario)

    open_panel("Importação inteligente", "Suba foto/PDF, revise o que o sistema entendeu e confirme antes de salvar.")

    st.warning(
        "Receita manuscrita pode ser lida com erro. Esta tela é assistida: o sistema sugere, mas quem confirma é o usuário."
    )

    arquivo = st.file_uploader("Suba foto, PDF ou TXT", type=["pdf", "txt", "png", "jpg", "jpeg", "webp"])
    texto_manual = st.text_area(
        "Texto extraído ou revisado",
        height=220,
        placeholder="Se a imagem não tiver OCR local, digite/cole aqui o texto da receita ou exame para o sistema interpretar.",
    )

    if st.button("Analisar documento"):
        analise = analisar_documento_saude(usuario_id, arquivo, texto_manual)
        st.session_state["analise_doc_saude"] = analise

    analise = st.session_state.get("analise_doc_saude")

    if not analise:
        st.info("Suba um documento e clique em Analisar documento.")
        close_panel()
        return

    st.divider()

    st.write(f"**Leitura:** {analise['status_leitura']}")
    st.write(f"**Tipo provável:** {analise['tipo_documento']}")

    paciente_detectado_final = analise.get("paciente_detectado") or ""
    validacao_final = analise.get("validacao_paciente") or ""

    st.subheader("Confirmação do paciente")

    if paciente_detectado_final:
        st.write(f"Paciente detectado no documento: **{paciente_detectado_final}**")

    if str(validacao_final).startswith("ALERTA"):
        st.error(validacao_final)
        modo_paciente = st.radio(
            "Como deseja proceder?",
            [
                "Cancelar/revisar antes de salvar",
                f"Confirmar que pertence a {nome_ativo}",
                "Salvar como paciente não identificado",
            ],
            key="modo_paciente_alerta",
        )
    elif not paciente_detectado_final:
        st.warning(
            "Não foi possível identificar o nome do paciente no documento. Isso é comum em receita manuscrita ou foto com baixa leitura."
        )
        modo_paciente = st.radio(
            "Este documento pertence a quem?",
            [
                f"Pertence a {nome_ativo}",
                "Não sei / revisar depois",
                "Vou informar manualmente o nome lido",
            ],
            key="modo_paciente_nao_detectado",
        )
    else:
        st.success(validacao_final)
        modo_paciente = f"Pertence a {nome_ativo}"

    if modo_paciente == "Cancelar/revisar antes de salvar":
        salvar_mesmo = False
        st.info("Revise o usuário ativo, o texto extraído ou mova o documento depois pela Central de correções.")
    elif modo_paciente == f"Confirmar que pertence a {nome_ativo}" or modo_paciente == f"Pertence a {nome_ativo}":
        salvar_mesmo = True
        paciente_detectado_final = nome_ativo
        validacao_final = f"Confirmado manualmente pelo usuário: documento pertence a {nome_ativo}."
        st.success(validacao_final)
    elif modo_paciente == "Vou informar manualmente o nome lido":
        nome_manual = st.text_input("Nome do paciente conforme você leu no documento", value=nome_ativo)
        paciente_detectado_final = nome_manual.strip()
        if nome_manual.strip().lower() == nome_ativo.strip().lower():
            validacao_final = f"Confirmado manualmente: documento pertence a {nome_ativo}."
            salvar_mesmo = True
            st.success(validacao_final)
        else:
            validacao_final = f"Nome informado manualmente: {nome_manual}. Usuário ativo: {nome_ativo}."
            salvar_mesmo = st.checkbox("Salvar mesmo assim neste cadastro", key="salvar_nome_manual_divergente")
            if salvar_mesmo:
                st.warning("Documento será salvo no usuário ativo, apesar do nome manual ser diferente.")
    else:
        salvar_mesmo = True
        paciente_detectado_final = "Paciente não identificado"
        validacao_final = "Paciente não identificado. Documento salvo para revisão posterior."
        st.warning(validacao_final)

    with st.expander("Ver texto usado na análise"):
        texto_final = st.text_area("Texto final para salvar no histórico", value=analise["texto"], height=260)
        analise["texto"] = texto_final

    st.divider()

    st.subheader("1. Marco da jornada")

    criar_marco = st.checkbox("Criar um marco para este documento", value=True)
    marco_id_final = None

    if criar_marco:
        c1, c2 = st.columns(2)
        with c1:
            data_marco = data_input_br("Data do marco", date.today(), key="imp_int_marco_data")
            tipo_marco = st.selectbox("Tipo de marco", ["Consulta médica", "Exame solicitado", "Início de tratamento", "Retorno médico", "Mudança de conduta", "Outro"])
            titulo_marco = st.text_input("Título do marco", value=f"{analise['tipo_documento']} importado")
        with c2:
            especialidade = st.text_input("Especialidade", placeholder="Ex.: Dermatologia")
            profissional = st.text_input("Profissional", value=analise.get("profissional") or "")
            local = st.text_input("Local")

        queixas = st.text_area("Queixas/motivo", placeholder="Ex.: acne, emagrecimento, controle de exames")
        conduta = st.text_area("Conduta observada", placeholder="Ex.: prescreveu medicamento, solicitou exames, retorno em 30 dias")
        proximo_passo = st.text_input("Próximo passo", placeholder="Ex.: retorno, repetir exames, comprar medicação")
    else:
        opcoes_marcos = listar_marcos_opcoes(usuario_id)
        marco_label = st.selectbox("Usar marco existente", list(opcoes_marcos.keys()))
        marco_id_final = opcoes_marcos[marco_label]

    st.divider()

    st.subheader("2. Medicamentos detectados")

    meds = analise["medicamentos"]
    if meds.empty:
        st.info("Nenhum medicamento detectado com segurança.")
        meds_edit = meds
    else:
        meds_edit = st.data_editor(
            meds,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "importar": st.column_config.CheckboxColumn("Importar"),
                "nome": "Medicamento",
                "dose": "Dose",
                "frequencia_modelo": st.column_config.SelectboxColumn(
                    "Frequência",
                    options=["1 vez ao dia", "2 vezes ao dia", "3 vezes ao dia", "4 vezes ao dia", "A cada X horas", "Horarios fixos", "Semanal"],
                ),
                "duracao": st.column_config.SelectboxColumn(
                    "Duração",
                    options=["7 dias", "14 dias", "30 dias", "Personalizado", "Uso continuo"],
                ),
                "confianca": "Confiança",
            },
            key="editor_meds_inteligente",
        )

    st.subheader("Plano sugerido de uso")
    if meds.empty:
        st.caption("Sem plano porque nenhum medicamento foi detectado.")
    else:
        from services.inteligencia_documentos_service import gerar_plano_uso_medicamentos
        st.dataframe(gerar_plano_uso_medicamentos(meds_edit), width="stretch", hide_index=True)

    st.divider()

    st.subheader("3. Exames detectados")

    exames = analise["exames"]
    if exames.empty:
        st.info("Nenhum exame detectado automaticamente.")
        exames_edit = exames
    else:
        exames_edit = st.data_editor(
            exames,
            width="stretch",
            hide_index=True,
            num_rows="dynamic",
            column_config={
                "importar": st.column_config.CheckboxColumn("Importar"),
                "nome_exame": "Exame",
                "resultado": "Resultado",
                "unidade": "Unidade",
                "referencia_min": "Ref. mínima",
                "referencia_max": "Ref. máxima",
                "confianca": "Confiança",
            },
            key="editor_exames_inteligente",
        )

    st.divider()

    st.subheader("4. Salvar documento e confirmar importação")

    with st.form("form_confirmar_importacao_inteligente"):
        data_doc = data_input_br("Data do documento", date.today(), key="imp_int_doc_data")
        titulo_doc = st.text_input("Título do documento", value=arquivo.name if arquivo else "Documento importado")
        tipo_doc = st.selectbox("Tipo de documento", ["Receita medica", "Exame", "Nota de consulta", "Relatorio medico", "Imagem", "Outro"], index=0 if analise["tipo_documento"] == "Receita medica" else 1 if analise["tipo_documento"] == "Exame" else 5)
        instituicao = st.text_input("Instituição / laboratório / clínica")
        relacionado_a = st.text_input("Relacionado a", placeholder="Ex.: Wegovy, Ferritina, consulta dermatologia")
        salvar_documento_flag = st.checkbox("Salvar arquivo/texto no repositório", value=True)
        criar_pendencias_revisao = st.checkbox("Criar pendência para revisar itens de baixa confiança", value=True)

        confirmar = st.form_submit_button("Confirmar e salvar tudo revisado")

        if confirmar:
            if not salvar_mesmo:
                st.warning("Confirme o paciente antes de salvar.")
                close_panel()
                return

            if criar_marco:
                marco_id_final = salvar_marco(
                    usuario_id=usuario_id,
                    data_marco=data_marco,
                    tipo_marco=tipo_marco,
                    titulo=titulo_marco,
                    especialidade=especialidade,
                    profissional=profissional,
                    local=local,
                    queixas=queixas,
                    motivo=queixas,
                    conduta=conduta,
                    exames_solicitados=", ".join(exames_edit[exames_edit["importar"] == True]["nome_exame"].tolist()) if not exames_edit.empty else "",
                    medicamentos_relacionados=", ".join(meds_edit[meds_edit["importar"] == True]["nome"].tolist()) if not meds_edit.empty else "",
                    proximo_passo=proximo_passo,
                    observacao="Marco criado a partir da importação inteligente.",
                )

            documento_id = None
            if salvar_documento_flag:
                documento_id = salvar_documento(
                    usuario_id=usuario_id,
                    tipo=tipo_doc,
                    data_doc=data_doc,
                    titulo=titulo_doc,
                    profissional=analise.get("profissional") or "",
                    instituicao=instituicao,
                    arquivo=arquivo,
                    relacionado_a=relacionado_a,
                    observacao=analise["texto"][:3000],
                    paciente_detectado=paciente_detectado_final,
                    validacao_paciente=validacao_final,
                    marco_id=marco_id_final,
                )

            meds_salvos = 0
            if not meds_edit.empty:
                selecionados = meds_edit[meds_edit["importar"] == True]
                for _, r in selecionados.iterrows():
                    duracao = r.get("duracao") or "Personalizado"
                    dias = int(r.get("dias_personalizados") or 30)
                    data_fim = date.today() + timedelta(days=max(dias - 1, 0))

                    salvar_medicamento(
                        usuario_id=usuario_id,
                        nome=str(r.get("nome") or "").strip(),
                        dose=str(r.get("dose") or "").strip(),
                        modelo=str(r.get("frequencia_modelo") or "1 vez ao dia"),
                        intervalo_horas=int(r.get("intervalo_horas")) if pd.notna(r.get("intervalo_horas")) and str(r.get("intervalo_horas")).strip() else None,
                        horarios_fixos="",
                        horario_inicial=_hora_from_str(r.get("horario_inicial"), time(8, 0)),
                        data_inicio=date.today(),
                        duracao=duracao,
                        data_fim=data_fim if duracao == "Personalizado" else None,
                        orientacao=str(r.get("orientacao") or ""),
                        medico=analise.get("profissional") or "",
                        marco_id=marco_id_final,
                    )
                    meds_salvos += 1

                    if criar_pendencias_revisao and str(r.get("confianca") or "") == "Baixa":
                        criar_pendencia(
                            usuario_id=usuario_id,
                            tipo="Revisar importação",
                            prioridade="Média",
                            titulo=f"Revisar medicamento importado: {r.get('nome')}",
                            descricao="O medicamento foi detectado com baixa confiança. Confirmar nome, dose e orientação com receita, farmácia ou profissional.",
                            origem="Importação inteligente",
                            marco_id=marco_id_final,
                        )

            exames_salvos = 0
            if not exames_edit.empty:
                selecionados = exames_edit[exames_edit["importar"] == True]
                for _, r in selecionados.iterrows():
                    salvar_exame(
                        usuario_id=usuario_id,
                        data_exame=data_doc,
                        nome_exame=str(r.get("nome_exame") or "").strip(),
                        resultado=float(r.get("resultado") or 0),
                        unidade=str(r.get("unidade") or ""),
                        referencia_min=float(r.get("referencia_min") or 0),
                        referencia_max=float(r.get("referencia_max") or 0),
                        laboratorio=instituicao,
                        observacao=str(r.get("observacao") or ""),
                        marco_id=marco_id_final,
                    )
                    exames_salvos += 1

                    if criar_pendencias_revisao and str(r.get("confianca") or "") == "Baixa":
                        criar_pendencia(
                            usuario_id=usuario_id,
                            tipo="Revisar importação",
                            prioridade="Média",
                            titulo=f"Revisar exame importado: {r.get('nome_exame')}",
                            descricao="O exame foi detectado com baixa confiança. Confirmar resultado, unidade e referência antes de usar na análise.",
                            origem="Importação inteligente",
                            marco_id=marco_id_final,
                        )

            salvar_importacao_assistida(
                usuario_id=usuario_id,
                tipo_documento=tipo_doc,
                titulo=titulo_doc,
                paciente_detectado=paciente_detectado_final,
                validacao_paciente=validacao_final,
                texto_extraido=analise["texto"],
                documento_id=documento_id,
                status="Confirmada",
            )

            st.success(f"Importação concluída: {meds_salvos} medicamento(s), {exames_salvos} exame(s), documento {'salvo' if documento_id else 'não salvo'} e marco {'criado/vinculado' if marco_id_final else 'não vinculado'}.")
            st.session_state.pop("analise_doc_saude", None)
            recarregar()

    close_panel()
