from __future__ import annotations

import uuid
from typing import List, Optional

import streamlit as st

from backend.db.client import get_session
from backend.db.cruds import (
    init_db,
    list_personas,
    create_persona,
    list_reports_for_persona,
)
from backend.db.models import PersonaCreate, PersonaRead, ReportRead
from ui import ChatPage


class AssistantApp:
    def __init__(self) -> None:
        init_db()
        self.user_id = self._ensure_user_id()
        self.chat_page = ChatPage(self.user_id)

    def run(self) -> None:
        st.set_page_config(page_title="8-Fold Assistant", layout="wide")
        personas = self._load_personas()
        persona_id, persona = self._render_sidebar(personas)
        self._render_header(persona)

        self.chat_page.render(persona_id)

    def _ensure_user_id(self) -> str:
        if "ui_user_id" not in st.session_state:
            st.session_state["ui_user_id"] = f"streamlit-{uuid.uuid4()}"
        return st.session_state["ui_user_id"]

    def _load_personas(self) -> List[PersonaRead]:
        with get_session() as db:
            return list_personas(db)

    def _render_sidebar(
        self,
        personas: List[PersonaRead],
    ) -> tuple[Optional[uuid.UUID], Optional[PersonaRead]]:
        st.sidebar.header("Personas")
        persona_id: Optional[uuid.UUID] = None
        persona: Optional[PersonaRead] = None

        if personas:
            labels = [
                f"{p.name} ({p.role or 'Unknown role'})"
                for p in personas
            ]
            default_index = 0
            selected = st.sidebar.selectbox(
                "Active persona",
                options=labels,
                index=default_index,
                key="persona_select",
            )
            idx = labels.index(selected)
            persona = personas[idx]
            persona_id = persona.id
        else:
            st.sidebar.info("Create a persona to begin.")

        self._persona_form()

        if persona_id:
            reports = self._load_reports(persona_id)
            with st.sidebar.expander("Recent research", expanded=False):
                if reports:
                    for report in reports:
                        created = report.created_at.strftime("%Y-%m-%d")
                        label = report.company_name
                        if report.report_json.get("comparison_pair"):
                            label += " (comparison)"
                        st.write(f"{label} • {created}")
                else:
                    st.write("No research yet.")

        return persona_id, persona

    def _persona_form(self) -> None:
        with st.sidebar.expander("New persona", expanded=False):
            with st.form("persona_form", clear_on_submit=True):
                name = st.text_input("Name")
                role = st.text_input("Role")
                company = st.text_input("Company")
                region = st.text_input("Region")
                goal = st.text_input("Goal")
                notes = st.text_area("Notes")
                submitted = st.form_submit_button("Save persona")
            if submitted and name.strip():
                data = PersonaCreate(
                    name=name.strip(),
                    role=role.strip() or None,
                    company=company.strip() or None,
                    region=region.strip() or None,
                    goal=goal.strip() or None,
                    notes=notes.strip() or None,
                )
                with get_session() as db:
                    create_persona(db, data)
                st.success("Persona saved.")
                st.rerun()
            elif submitted:
                st.warning("Name is required to create a persona.")

    def _load_reports(self, persona_id: uuid.UUID) -> List[ReportRead]:
        with get_session() as db:
            reports = list_reports_for_persona(db, persona_id)
            return reports[:5]

    def _render_header(self, persona: Optional[PersonaRead]) -> None:
        st.title("8-Fold Assistant")
        if not persona:
            st.info("Select or create a persona to get started.")
            return
        details = f"{persona.name}"
        if persona.role:
            details += f" • {persona.role}"
        if persona.company:
            details += f" at {persona.company}"
        st.caption(details)
        if persona.goal:
            st.write(f"Goal: {persona.goal}")
        if persona.notes:
            st.write(persona.notes)


def main() -> None:
    AssistantApp().run()


if __name__ == "__main__":
    main()


