from core.database import consultar_df, executar
from core.helpers import agora, hoje_iso
from services.medicamentos_service import marcar_dose


def registrar_rapido(usuario_id, categoria, texto):
    return executar(
        """
        INSERT INTO registros_rapidos (usuario_id, data_registro, categoria, texto, criado_em)
        VALUES (?, ?, ?, ?, ?)
        """,
        (usuario_id, hoje_iso(), categoria, texto, agora()),
    )


def tentar_comando_rapido(usuario_id, texto):
    txt = texto.lower().strip()
    if not txt:
        return "Digite ou dite um comando."

    registrar_rapido(usuario_id, "Comando", texto)

    meds = consultar_df(
        """
        SELECT id, nome
        FROM medicamentos
        WHERE usuario_id = ?
          AND COALESCE(status, 'Ativo') = 'Ativo'
        ORDER BY LENGTH(nome) DESC
        """,
        (usuario_id,),
    )

    med = None
    for _, r in meds.iterrows():
        if str(r["nome"]).lower() in txt:
            med = r
            break

    if med is None:
        return "Comando salvo, mas nao encontrei medicamento ativo com esse nome."

    med_id = int(med["id"])

    if "tomei" in txt or "tomado" in txt:
        dose = consultar_df(
            """
            SELECT *
            FROM doses
            WHERE usuario_id = ?
              AND medicamento_id = ?
              AND data_prevista = ?
              AND status = 'Pendente'
            ORDER BY horario_previsto
            LIMIT 1
            """,
            (usuario_id, med_id, hoje_iso()),
        )

        if dose.empty:
            return f"Nao encontrei dose pendente hoje para {med['nome']}."

        marcar_dose(int(dose.iloc[0]["id"]), usuario_id, "Tomado", f"Comando rapido: {texto}")
        return f"Dose marcada como tomada: {med['nome']}."

    if "passei mal" in txt or "me fez mal" in txt or "enjoo" in txt or "tontura" in txt or "mal estar" in txt:
        executar(
            """
            INSERT INTO eventos_medicacao (
                usuario_id, medicamento_id, data_evento, tipo_evento, motivo,
                sintomas, gravidade, observacao, criado_em
            )
            VALUES (?, ?, ?, 'Efeito adverso', 'Relato do usuario', ?, 'A avaliar', ?, ?)
            """,
            (usuario_id, med_id, hoje_iso(), texto, texto, agora()),
        )
        return f"Evento adverso registrado para {med['nome']}."

    return "Comando salvo. Use exemplos como: 'tomei Neural agora' ou 'passei mal com Neural'."
