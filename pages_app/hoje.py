import streamlit as st

from components.cards import open_panel, close_panel
from core.helpers import br_date, hoje_iso, recarregar
from core.database import consultar_df
from services.medicamentos_service import listar_doses_hoje, marcar_dose


def render_hoje(usuario_id):
    doses_hoje = listar_doses_hoje(usuario_id)

    open_panel("Agenda de hoje")
    if doses_hoje.empty:
        st.success("Nenhuma dose prevista para hoje.")
    else:
        for _, r in doses_hoje.iterrows():
            st.write("---")
            c1, c2, c3, c4 = st.columns([1, 3, 2, 3])
            with c1:
                st.write(f"**{r['horario_previsto']}**")
            with c2:
                st.write(f"**{r['medicamento']}**")
                st.caption(r["dose"] if r["dose"] else "")
            with c3:
                if r["status"] == "Tomado":
                    st.success(f"Tomado as {r['horario_tomado']}")
                elif r["status"] == "Pendente":
                    st.warning("Pendente")
                else:
                    st.info(r["status"])
            with c4:
                if r["status"] == "Pendente":
                    if st.button("Tomei", key=f"tomar_{r['id']}"):
                        marcar_dose(int(r["id"]), usuario_id, "Tomado")
                        recarregar()
                    if st.button("Esqueci", key=f"esq_{r['id']}"):
                        marcar_dose(int(r["id"]), usuario_id, "Esquecido")
                        recarregar()
    close_panel()

    open_panel("Proximos 7 dias")
    from datetime import date, timedelta
    agenda = consultar_df(
        """
        SELECT d.data_prevista, d.horario_previsto, d.status, m.nome AS medicamento, m.dose
        FROM doses d
        JOIN medicamentos m ON m.id = d.medicamento_id
        WHERE d.usuario_id = ?
          AND d.data_prevista BETWEEN ? AND ?
        ORDER BY d.data_prevista, d.horario_previsto
        """,
        (usuario_id, hoje_iso(), (date.today() + timedelta(days=6)).isoformat()),
    )
    if agenda.empty:
        st.info("Sem doses nos proximos 7 dias.")
    else:
        agenda["data"] = agenda["data_prevista"].apply(br_date)
        st.dataframe(agenda[["data", "horario_previsto", "medicamento", "dose", "status"]], width="stretch", hide_index=True)
    close_panel()
