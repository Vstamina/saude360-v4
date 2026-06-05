from datetime import date, time, timedelta

import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import data_input_br, recarregar
from services.documentos_service import salvar_documento, validar_paciente_documento
from services.exames_service import salvar_exame
from services.medicamentos_service import salvar_medicamento
from services.marcos_service import listar_marcos_opcoes
from services.importador_service import (
    extrair_texto_arquivo,
    extrair_exames_de_texto,
    sugerir_medicamento_de_texto,
    detectar_data_texto,
)


def render_importar_documento(usuario_id, usuario=None):
    open_panel("Importar documento", "Upload + leitura de PDF textual/TXT + importacao assistida com alerta de paciente")

    tipo_importacao = st.selectbox(
        "O que voce quer importar?",
        ["Exames laboratoriais", "Receita / medicamento", "Apenas salvar documento"],
    )

    arquivo = st.file_uploader(
        "Suba PDF, TXT ou imagem",
        type=["pdf", "txt", "png", "jpg", "jpeg", "webp"],
    )

    texto_extraido = ""
    status_leitura = ""

    if arquivo is not None:
        texto_extraido, status_leitura = extrair_texto_arquivo(arquivo)
        st.info(status_leitura)

    texto_manual = st.text_area(
        "Texto extraido ou colado para leitura assistida",
        value=texto_extraido,
        height=220,
        help="Se for foto/receita manuscrita, cole aqui o texto digitado ou revisado.",
    )

    paciente_detectado, validacao_paciente = validar_paciente_documento(usuario_id, texto_manual)

    if paciente_detectado:
        st.write(f"Paciente detectado no documento: **{paciente_detectado}**")

    if validacao_paciente.startswith("ALERTA"):
        st.error(validacao_paciente)
        salvar_mesmo = st.checkbox("Salvar/importar mesmo com alerta de paciente divergente")
    else:
        st.success(validacao_paciente)
        salvar_mesmo = True

    opcoes_marcos = listar_marcos_opcoes(usuario_id)
    marco_label_global = st.selectbox("Relacionado a qual consulta/marco?", list(opcoes_marcos.keys()))
    marco_id_global = opcoes_marcos[marco_label_global]

    st.divider()

    if tipo_importacao == "Apenas salvar documento":
        st.subheader("Salvar no repositorio")

        with st.form("form_salvar_doc_importador"):
            data_doc = data_input_br("Data do documento", detectar_data_texto(texto_manual), key="imp_doc_data")
            tipo_doc = st.selectbox("Tipo", ["Receita medica", "Exame", "Nota de consulta", "Nota de farmacia", "Atestado", "Relatorio medico", "Imagem", "Outro"])
            titulo = st.text_input("Titulo", value=arquivo.name if arquivo else "")
            profissional = st.text_input("Profissional")
            instituicao = st.text_input("Instituicao")
            relacionado_a = st.text_input("Relacionado a")
            observacao = st.text_area("Observacao", value=texto_manual[:1000])

            if st.form_submit_button("Salvar documento"):
                if not salvar_mesmo:
                    st.warning("Confirme que deseja salvar mesmo com alerta de paciente divergente.")
                elif not titulo.strip():
                    st.warning("Informe um titulo.")
                else:
                    salvar_documento(
                        usuario_id, tipo_doc, data_doc, titulo, profissional, instituicao,
                        arquivo, relacionado_a, observacao, paciente_detectado, validacao_paciente,
                        marco_id=marco_id_global
                    )
                    st.success("Documento salvo no repositorio.")
                    recarregar()

    elif tipo_importacao == "Exames laboratoriais":
        st.subheader("Importar exames")

        if st.button("Detectar exames no texto"):
            st.session_state["exames_detectados"] = extrair_exames_de_texto(texto_manual)

        df = st.session_state.get("exames_detectados")

        if df is None:
            st.info("Clique em 'Detectar exames no texto' para gerar uma tabela revisavel.")
        elif df.empty:
            st.warning("Nao detectei exames automaticamente. Tente colar linhas como: Ferritina 32,20 ng/mL 30 a 300.")
        else:
            st.write("Revise antes de salvar. O sistema nao deve importar sem confirmacao.")
            editado = st.data_editor(
                df,
                width="stretch",
                hide_index=True,
                num_rows="dynamic",
                column_config={
                    "importar": st.column_config.CheckboxColumn("Importar"),
                    "nome_exame": "Exame",
                    "resultado": "Resultado",
                    "unidade": "Unidade",
                    "referencia_min": "Ref. minima",
                    "referencia_max": "Ref. maxima",
                    "observacao": "Observacao",
                },
            )

            with st.form("form_confirmar_exames_importados"):
                data_exame = data_input_br("Data do exame", detectar_data_texto(texto_manual), key="imp_exame_data")
                laboratorio = st.text_input("Laboratorio")
                titulo_doc = st.text_input("Titulo do documento", value=arquivo.name if arquivo else "Documento de exames")
                salvar_doc = st.checkbox("Salvar tambem o arquivo no repositorio", value=True)

                if st.form_submit_button("Salvar exames selecionados"):
                    if not salvar_mesmo:
                        st.warning("Confirme que deseja importar mesmo com alerta de paciente divergente.")
                    else:
                        selecionados = editado[editado["importar"] == True]
                        if selecionados.empty:
                            st.warning("Nenhum exame selecionado.")
                        else:
                            for _, r in selecionados.iterrows():
                                salvar_exame(
                                    usuario_id=usuario_id,
                                    data_exame=data_exame,
                                    nome_exame=str(r["nome_exame"]),
                                    resultado=float(r["resultado"]),
                                    unidade=str(r["unidade"] or ""),
                                    referencia_min=float(r["referencia_min"] or 0),
                                    referencia_max=float(r["referencia_max"] or 0),
                                    laboratorio=laboratorio,
                                    observacao=str(r["observacao"] or ""),
                                    marco_id=marco_id_global,
                                )

                            if salvar_doc:
                                salvar_documento(
                                    usuario_id=usuario_id,
                                    tipo="Exame",
                                    data_doc=data_exame,
                                    titulo=titulo_doc,
                                    profissional="",
                                    instituicao=laboratorio,
                                    arquivo=arquivo,
                                    relacionado_a="Exames importados",
                                    observacao=texto_manual[:1000],
                                    paciente_detectado=paciente_detectado,
                                    validacao_paciente=validacao_paciente,
                                    marco_id=marco_id_global,
                                )

                            st.success(f"{len(selecionados)} exame(s) salvo(s).")
                            st.session_state.pop("exames_detectados", None)
                            recarregar()

    elif tipo_importacao == "Receita / medicamento":
        st.subheader("Importar receita / medicamento")

        if st.button("Sugerir medicamento a partir do texto"):
            st.session_state["med_sugerido"] = sugerir_medicamento_de_texto(texto_manual)

        sug = st.session_state.get("med_sugerido")

        if sug is None:
            st.info("Clique em 'Sugerir medicamento a partir do texto'. Depois revise tudo antes de salvar.")
        else:
            with st.form("form_confirmar_medicamento_importado"):
                nome = st.text_input("Nome do medicamento", value=sug.get("nome", ""))
                dose = st.text_input("Dose", value=sug.get("dose", ""))

                modelos = ["1 vez ao dia", "2 vezes ao dia", "3 vezes ao dia", "4 vezes ao dia", "A cada X horas", "Horarios fixos", "Semanal"]
                modelo_sug = sug.get("frequencia_modelo", "1 vez ao dia")
                if modelo_sug not in modelos:
                    modelo_sug = "1 vez ao dia"

                modelo = st.selectbox("Frequencia", modelos, index=modelos.index(modelo_sug))

                intervalo_horas = None
                horarios_fixos = ""
                if modelo == "A cada X horas":
                    intervalo_horas = st.number_input("Tomar a cada quantas horas?", min_value=1, max_value=24, value=int(sug.get("intervalo_horas") or 8), step=1)
                if modelo == "Horarios fixos":
                    horarios_fixos = st.text_input("Horarios fixos", value="08:00, 20:00")

                horario_inicial = st.time_input("Horario inicial", value=time(8, 0))
                data_inicio = data_input_br("Data de inicio", date.today(), key="imp_med_inicio")

                duracoes = ["7 dias", "14 dias", "30 dias", "Personalizado", "Uso continuo"]
                duracao_sug = sug.get("duracao", "Personalizado")
                if duracao_sug not in duracoes:
                    duracao_sug = "Personalizado"

                duracao = st.selectbox("Duracao", duracoes, index=duracoes.index(duracao_sug))

                data_fim = None
                if duracao == "Personalizado":
                    dias = int(sug.get("dias_personalizados") or 7)
                    data_fim = data_input_br("Data de fim", date.today() + timedelta(days=max(dias - 1, 0)), key="imp_med_fim")

                medico = st.text_input("Medico/profissional")
                orientacao = st.text_area("Orientacao", value=sug.get("orientacao", ""))
                salvar_doc = st.checkbox("Salvar tambem a receita no repositorio", value=True)
                titulo_doc = st.text_input("Titulo da receita", value=arquivo.name if arquivo else "Receita importada")

                if st.form_submit_button("Salvar medicamento revisado"):
                    if not salvar_mesmo:
                        st.warning("Confirme que deseja importar mesmo com alerta de paciente divergente.")
                    elif not nome.strip():
                        st.warning("Informe o nome do medicamento.")
                    else:
                        salvar_medicamento(
                            usuario_id=usuario_id,
                            nome=nome,
                            dose=dose,
                            modelo=modelo,
                            intervalo_horas=intervalo_horas,
                            horarios_fixos=horarios_fixos,
                            horario_inicial=horario_inicial,
                            data_inicio=data_inicio,
                            duracao=duracao,
                            data_fim=data_fim,
                            orientacao=orientacao,
                            medico=medico,
                            marco_id=marco_id_global,
                        )

                        if salvar_doc:
                            salvar_documento(
                                usuario_id=usuario_id,
                                tipo="Receita medica",
                                data_doc=data_inicio,
                                titulo=titulo_doc,
                                profissional=medico,
                                instituicao="",
                                arquivo=arquivo,
                                relacionado_a=nome,
                                observacao=texto_manual[:1000],
                                paciente_detectado=paciente_detectado,
                                validacao_paciente=validacao_paciente,
                                marco_id=marco_id_global,
                            )

                        st.success("Medicamento salvo e agenda gerada.")
                        st.session_state.pop("med_sugerido", None)
                        recarregar()

    close_panel()
