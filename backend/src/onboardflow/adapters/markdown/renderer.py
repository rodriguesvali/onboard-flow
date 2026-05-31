from onboardflow.domain.models import OnboardingPlanResult, ResultItem


class MarkdownRenderer:
    def render(self, plan: OnboardingPlanResult) -> str:
        sections = [
            "# Plano de Onboarding",
            "",
            "## Perfil do colaborador",
            f"- Nome: {plan.employee_profile.full_name}",
            f"- Cargo: {plan.employee_profile.role}",
            f"- Departamento: {plan.employee_profile.department}",
            f"- Gestor: {plan.employee_profile.direct_manager}",
            f"- Inicio: {plan.employee_profile.start_date}",
            "",
            "## Resumo executivo",
            plan.executive_summary,
            "",
            self._items("Documentos obrigatorios", plan.required_documents),
            self._items("Checklist de TI", plan.it_checklist),
            self._items("Trilha de treinamento", plan.training_path),
            self._items("Agenda inicial", plan.initial_agenda),
            "## Comunicados em rascunho",
        ]
        for communication in plan.communications:
            sections.extend(
                [
                    f"### {communication.subject}",
                    f"Publico: {communication.audience}",
                    communication.body,
                    "Requer revisao humana antes de envio.",
                    "",
                ]
            )
        sections.extend(
            [
                self._items("Pendencias", plan.pending_actions),
                self._items("Riscos", plan.risk_flags),
                "## Proximas acoes recomendadas",
            ]
        )
        sections.extend([f"- {action}" for action in plan.next_recommended_actions])
        sections.append("")
        return "\n".join(sections)

    def _items(self, title: str, items: list[ResultItem]) -> str:
        lines = [f"## {title}"]
        if not items:
            lines.append("- Nenhum item identificado.")
        for item in items:
            rationale = f" — {item.rationale}" if item.rationale else ""
            lines.append(f"- [{item.status}] {item.title} ({item.owner_role}){rationale}")
        lines.append("")
        return "\n".join(lines)

