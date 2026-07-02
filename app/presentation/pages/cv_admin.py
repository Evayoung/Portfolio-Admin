"""CV workspace for Neo Admin."""

from __future__ import annotations

from fasthtml.common import Button, Div, Form, H2, H3, Input, P, Span, Strong, Textarea
from faststrap import Badge, Card, Col, EmptyState, Modal, Row, SEO

from app.config import settings
from app.infrastructure.cv_repository import (
    get_cv_meta,
    get_cv_workspace_summary,
    list_certifications,
    list_competencies,
    list_core_skills,
    list_education,
    list_languages,
    list_tool_categories,
    list_work_history,
)
from app.infrastructure.supabase_client import service_role_is_configured
from app.presentation.page_helpers import SectionWrap, floating_field, loading_action_button, status_alert, summary_card, textarea_field
from app.presentation.shell import page_frame


def cv_save_status_fragment(title: str, message: str, tone: str = "info") -> Div:
    return status_alert(title, message, tone)


def _stack_panel(title: str, lines: list[str]) -> Card:
    return Card(
        Div(
            H3(title, cls="admin-subsection-title"),
            Div(*[Div(item, cls="admin-stack-line") for item in lines], cls="admin-stack-list"),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )


# ── Section management cards (replace textareas in the editor) ──

def _manage_card(title: str, count: int, noun: str, modal_id: str) -> Div:
    plural = noun if count == 1 else noun + "s"
    return Div(
        Div(
            Div(
                Span(title, cls="cv-section-card-title"),
                Span(f"{count} {plural}", cls="cv-section-card-count"),
                cls="d-flex justify-content-between align-items-center gap-3"
            ),
            Button("Manage", type="button", cls="btn admin-module-btn",
                   data_bs_toggle="modal", data_bs_target=f"#{modal_id}"),
            cls="d-flex justify-content-between align-items-center gap-2",
        ),
        cls="cv-section-card mt-3",
    )


# ── Modal helpers ──

def _simple_item_modal(modal_id, title, items, endpoint, add_label, instructions, template_id, template_html):
    """Build a modal for a simple single-field section (core_skills, competencies)."""
    item_rows = [
        Div(
            Input(type="text", cls="form-control admin-form-control", data_field="label",
                  value=label, placeholder=add_label),
            Button("x", type="button", cls="btn btn-outline-danger btn-sm flex-shrink-0",
                   onclick="removeCvItem(this)", style="height:2.4rem;"),
            cls="cv-item-row d-flex gap-2 align-items-center",
            data_item_row="",
        )
        for label in items
    ]
    return Modal(
        Div(
            P(instructions, cls="admin-module-copy"),
            Form(
                Div(*item_rows, id=f"{modal_id}-items", cls="cv-items-container", data_items_container=""),
                template_html,
                Input(type="hidden", name="data", id=f"{modal_id}-data"),
                Div(id=f"{modal_id}-status"),
                Div(
                    Button(f"+ Add {add_label}", type="button", cls="btn admin-install-btn",
                           onclick=f"addCvItem('{modal_id}-items', '{template_id}')"),
                    loading_action_button(f"Save {title}", endpoint=endpoint, target=f"#{modal_id}-status"),
                    cls="cv-section-modal-footer",
                ),
                cls="cv-section-form",
                hx_post=endpoint,
                hx_target=f"#{modal_id}-status",
            ),
        ),
        modal_id=modal_id,
        title=title,
        size="lg",
        centered=True,
    )


def _work_history_modal(items) -> Modal:
    rid = "wh"
    rows = []
    for item in items:
        rows.append(Div(
            Div(
                Div(Input(type="text", cls="form-control admin-form-control", data_field="title",
                          value=item.title, placeholder="Title"), cls="col-md-4"),
                Div(Input(type="text", cls="form-control admin-form-control", data_field="organisation",
                          value=item.organisation, placeholder="Organisation"), cls="col-md-4"),
                Div(Input(type="text", cls="form-control admin-form-control", data_field="period",
                          value=item.period, placeholder="Period"), cls="col-md-2"),
                Div(Button("x", type="button", cls="btn btn-outline-danger btn-sm",
                           onclick="removeCvItem(this)"), cls="col-md-2 d-flex align-items-end"),
                cls="row g-2",
            ),
            Div(
                Div(Input(type="text", cls="form-control admin-form-control", data_field="location",
                          value=item.location, placeholder="Location"), cls="col-md-4"),
                Div(Textarea("; ".join(item.bullets), cls="form-control admin-form-control cv-bullets-field",
                             data_field="bullets", rows=1, placeholder="Bullets (semicolon-separated)"), cls="col-md-8"),
                cls="row g-2 mt-1",
            ),
            cls="cv-item-row", data_item_row="",
        ))
    return Modal(
        Div(
            P("Manage work history. Add, edit, or remove work experience entries.", cls="admin-module-copy"),
            Form(
                Div(*rows, id=f"{rid}-items", cls="cv-items-container", data_items_container=""),
                _TEMPLATES["wh"],
                Input(type="hidden", name="data", id=f"{rid}-data"),
                Div(id=f"{rid}-status"),
                Div(
                    Button("+ Add Role", type="button", cls="btn admin-install-btn",
                           onclick=f"addCvItem('{rid}-items', '{rid}-template')"),
                    loading_action_button("Save Experience", endpoint="/cv/section/work_history/save", target="#wh-status"),
                    cls="cv-section-modal-footer",
                ),
                cls="cv-section-form",
                hx_post="/cv/section/work_history/save",
                hx_target=f"#{rid}-status",
            ),
        ),
        modal_id="work-history-modal",
        title="Work History",
        size="xl",
        centered=True,
    )


def _education_modal(items) -> Modal:
    rid = "edu"
    item_rows = []
    for item in items:
        main_row = Div(
            Div(Input(type="text", cls="form-control admin-form-control", data_field="degree",
                      value=item.degree, placeholder="Degree"), cls="col-md-4"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="institution",
                      value=item.institution, placeholder="Institution"), cls="col-md-4"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="period",
                      value=item.period, placeholder="Period"), cls="col-md-2"),
            Div(Button("x", type="button", cls="btn btn-outline-danger btn-sm",
                       onclick="removeCvItem(this)"), cls="col-md-2 d-flex align-items-end"),
            cls="row g-2",
        )
        note_row = Div(
            Div(Input(type="text", cls="form-control admin-form-control", data_field="note",
                      value=item.note, placeholder="Note (optional)"), cls="col-md-12"),
            cls="row g-2 mt-1",
        )
        item_rows.append(Div(main_row, note_row, cls="cv-item-row", data_item_row=""))

    return Modal(
        Div(
            P("Manage education entries. Add, edit, or remove education records.", cls="admin-module-copy"),
            Form(
                Div(*item_rows, id=f"{rid}-items", cls="cv-items-container", data_items_container=""),
                _TEMPLATES["edu"],
                Input(type="hidden", name="data", id=f"{rid}-data"),
                Div(id=f"{rid}-status"),
                Div(
                    Button("+ Add Entry", type="button", cls="btn admin-install-btn",
                           onclick=f"addCvItem('{rid}-items', '{rid}-template')"),
                    loading_action_button("Save Education", endpoint="/cv/section/education/save", target="#edu-status"),
                    cls="cv-section-modal-footer",
                ),
                cls="cv-section-form",
                hx_post="/cv/section/education/save",
                hx_target=f"#{rid}-status",
            ),
        ),
        modal_id="education-modal",
        title="Education",
        size="xl",
        centered=True,
    )


def _certifications_modal(items) -> Modal:
    rid = "cert"
    rows = [
        Div(
            Div(Input(type="text", cls="form-control admin-form-control", data_field="name",
                      value=item.name, placeholder="Certification name"), cls="col-md-4"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="issuer",
                      value=item.issuer, placeholder="Issuer"), cls="col-md-3"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="year",
                      value=item.year, placeholder="Year"), cls="col-md-2"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="credential_url",
                      value=item.credential_url, placeholder="URL"), cls="col-md-2"),
            Div(Button("x", type="button", cls="btn btn-outline-danger btn-sm",
                       onclick="removeCvItem(this)"), cls="col-md-1 d-flex align-items-end"),
            cls="row g-2", data_item_row="",
        )
        for item in items
    ]
    return Modal(
        Div(
            P("Manage certifications. Add, edit, or remove certification entries.", cls="admin-module-copy"),
            Form(
                Div(*rows, id=f"{rid}-items", cls="cv-items-container", data_items_container=""),
                _TEMPLATES["cert"],
                Input(type="hidden", name="data", id=f"{rid}-data"),
                Div(id=f"{rid}-status"),
                Div(
                    Button("+ Add Certification", type="button", cls="btn admin-install-btn",
                           onclick=f"addCvItem('{rid}-items', '{rid}-template')"),
                    loading_action_button("Save Certifications", endpoint="/cv/section/certifications/save", target="#cert-status"),
                    cls="cv-section-modal-footer",
                ),
                cls="cv-section-form",
                hx_post="/cv/section/certifications/save",
                hx_target=f"#{rid}-status",
            ),
        ),
        modal_id="certifications-modal",
        title="Certifications",
        size="xl",
        centered=True,
    )


def _tools_modal(items) -> Modal:
    rid = "tools"
    rows = [
        Div(
            Div(Input(type="text", cls="form-control admin-form-control", data_field="label",
                      value=item.label, placeholder="Category label"), cls="col-md-4"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="tools",
                      value=", ".join(item.tools), placeholder="Tool1, Tool2, ..."), cls="col-md-6"),
            Div(Button("x", type="button", cls="btn btn-outline-danger btn-sm",
                       onclick="removeCvItem(this)"), cls="col-md-2 d-flex align-items-end"),
            cls="row g-2", data_item_row="",
        )
        for item in items
    ]
    return Modal(
        Div(
            P("Manage tool categories. Each group has a label and comma-separated tools list.", cls="admin-module-copy"),
            Form(
                Div(*rows, id=f"{rid}-items", cls="cv-items-container", data_items_container=""),
                _TEMPLATES["tools"],
                Input(type="hidden", name="data", id=f"{rid}-data"),
                Div(id=f"{rid}-status"),
                Div(
                    Button("+ Add Group", type="button", cls="btn admin-install-btn",
                           onclick=f"addCvItem('{rid}-items', '{rid}-template')"),
                    loading_action_button("Save Tools", endpoint="/cv/section/tools/save", target="#tools-status"),
                    cls="cv-section-modal-footer",
                ),
                cls="cv-section-form",
                hx_post="/cv/section/tools/save",
                hx_target=f"#{rid}-status",
            ),
        ),
        modal_id="tools-modal",
        title="Tools & Technologies",
        size="xl",
        centered=True,
    )


def _languages_modal(items) -> Modal:
    rid = "lang"
    rows = [
        Div(
            Div(Input(type="text", cls="form-control admin-form-control", data_field="label",
                      value=item[0], placeholder="Language"), cls="col-md-4"),
            Div(Input(type="text", cls="form-control admin-form-control", data_field="proficiency_label",
                      value=item[1], placeholder="Level (e.g. Fluent)"), cls="col-md-4"),
            Div(Input(type="number", cls="form-control admin-form-control", data_field="proficiency_score",
                      value=str(item[2]), placeholder="0-100", min="0", max="100"), cls="col-md-2"),
            Div(Button("x", type="button", cls="btn btn-outline-danger btn-sm",
                       onclick="removeCvItem(this)"), cls="col-md-2 d-flex align-items-end"),
            cls="row g-2", data_item_row="",
        )
        for item in items
    ]
    return Modal(
        Div(
            P("Manage languages. Each entry has a name, proficiency level, and score (0-100).", cls="admin-module-copy"),
            Form(
                Div(*rows, id=f"{rid}-items", cls="cv-items-container", data_items_container=""),
                _TEMPLATES["lang"],
                Input(type="hidden", name="data", id=f"{rid}-data"),
                Div(id=f"{rid}-status"),
                Div(
                    Button("+ Add Language", type="button", cls="btn admin-install-btn",
                           onclick=f"addCvItem('{rid}-items', '{rid}-template')"),
                    loading_action_button("Save Languages", endpoint="/cv/section/languages/save", target="#lang-status"),
                    cls="cv-section-modal-footer",
                ),
                cls="cv-section-form",
                hx_post="/cv/section/languages/save",
                hx_target=f"#{rid}-status",
            ),
        ),
        modal_id="languages-modal",
        title="Languages",
        size="xl",
        centered=True,
    )


# ── Shared <template> elements for add-item rows ──

from fasthtml.common import NotStr

_TEMPLATES = {
    "cs": NotStr("""<template id="cs-template">
<div class="cv-item-row d-flex gap-2 align-items-center" data-item-row>
<input type="text" class="form-control admin-form-control" data-field="label" value="" placeholder="Skill name" />
<button type="button" class="btn btn-outline-danger btn-sm flex-shrink-0" onclick="removeCvItem(this)" style="height:2.4rem;">x</button>
</div>
</template>"""),
    "cp": NotStr("""<template id="cp-template">
<div class="cv-item-row d-flex gap-2 align-items-center" data-item-row>
<input type="text" class="form-control admin-form-control" data-field="label" value="" placeholder="Competency name" />
<button type="button" class="btn btn-outline-danger btn-sm flex-shrink-0" onclick="removeCvItem(this)" style="height:2.4rem;">x</button>
</div>
</template>"""),
    "wh": NotStr("""<template id="wh-template">
<div class="cv-item-row" data-item-row>
<div class="row g-2">
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="title" value="" placeholder="Title" /></div>
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="organisation" value="" placeholder="Organisation" /></div>
<div class="col-md-2"><input type="text" class="form-control admin-form-control" data-field="period" value="" placeholder="Period" /></div>
<div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCvItem(this)">x</button></div>
</div>
<div class="row g-2 mt-1">
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="location" value="" placeholder="Location" /></div>
<div class="col-md-8"><textarea class="form-control admin-form-control cv-bullets-field" data-field="bullets" rows="1" placeholder="Bullets (semicolon-separated)"></textarea></div>
</div>
</div>
</template>"""),
    "edu": NotStr("""<template id="edu-template">
<div class="cv-item-row" data-item-row>
<div class="row g-2">
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="degree" value="" placeholder="Degree" /></div>
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="institution" value="" placeholder="Institution" /></div>
<div class="col-md-2"><input type="text" class="form-control admin-form-control" data-field="period" value="" placeholder="Period" /></div>
<div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCvItem(this)">x</button></div>
</div>
<div class="row g-2 mt-1">
<div class="col-md-12"><input type="text" class="form-control admin-form-control" data-field="note" value="" placeholder="Note (optional)" /></div>
</div>
</div>
</template>"""),
    "cert": NotStr("""<template id="cert-template">
<div class="cv-item-row" data-item-row>
<div class="row g-2">
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="name" value="" placeholder="Certification name" /></div>
<div class="col-md-3"><input type="text" class="form-control admin-form-control" data-field="issuer" value="" placeholder="Issuer" /></div>
<div class="col-md-2"><input type="text" class="form-control admin-form-control" data-field="year" value="" placeholder="Year" /></div>
<div class="col-md-2"><input type="text" class="form-control admin-form-control" data-field="credential_url" value="" placeholder="URL" /></div>
<div class="col-md-1"><button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCvItem(this)">x</button></div>
</div>
</div>
</template>"""),
    "tools": NotStr("""<template id="tools-template">
<div class="cv-item-row" data-item-row>
<div class="row g-2">
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="label" value="" placeholder="Category label" /></div>
<div class="col-md-6"><input type="text" class="form-control admin-form-control" data-field="tools" value="" placeholder="Tool1, Tool2, ..." /></div>
<div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCvItem(this)">x</button></div>
</div>
</div>
</template>"""),
    "lang": NotStr("""<template id="lang-template">
<div class="cv-item-row" data-item-row>
<div class="row g-2">
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="label" value="" placeholder="Language" /></div>
<div class="col-md-4"><input type="text" class="form-control admin-form-control" data-field="proficiency_label" value="" placeholder="Level" /></div>
<div class="col-md-2"><input type="number" class="form-control admin-form-control" data-field="proficiency_score" value="" placeholder="0-100" min="0" max="100" /></div>
<div class="col-md-2"><button type="button" class="btn btn-outline-danger btn-sm" onclick="removeCvItem(this)">x</button></div>
</div>
</div>
</template>"""),
}


_TEMPLATE_BLOCK = NotStr("".join(str(v) for v in _TEMPLATES.values()))


# ── Main page ──

def cv_workspace_page() -> tuple:
    meta = get_cv_meta()
    summary = get_cv_workspace_summary()
    work_history = list_work_history()
    education = list_education()
    certifications = list_certifications()
    tool_categories = list_tool_categories()
    languages = list_languages()
    core_skills = list_core_skills()
    competencies = list_competencies()

    editor_form = Form(
        Row(
            Col(floating_field("Full Name", "name", meta.name, placeholder="Olorundare Micheal Babawale", required=True), span=12, md=6),
            Col(floating_field("Role", "role", meta.role, placeholder="Full-Stack & AI Systems Architect", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3",
        ),
        Row(
            Col(floating_field("Email", "email", meta.email, input_type="email", placeholder="name@example.com"), span=12, md=6),
            Col(floating_field("Phone", "phone", meta.phone, placeholder="+234..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(floating_field("WhatsApp", "whatsapp", meta.whatsapp, placeholder="+234..."), span=12, md=6),
            Col(floating_field("Location", "location", meta.location, placeholder="Ilorin, Nigeria"), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Row(
            Col(floating_field("GitHub URL", "github", meta.github, placeholder="https://github.com/..."), span=12, md=6),
            Col(floating_field("LinkedIn URL", "linkedin", meta.linkedin, placeholder="https://linkedin.com/in/..."), span=12, md=6, cls="mt-3 mt-md-0"),
            cls="g-3 mt-1",
        ),
        Div(textarea_field("Professional Summary", "summary", meta.summary, rows=7, required=True, placeholder="CV summary"), cls="mt-3"),

        # Section management cards (replace structured textareas)
        _manage_card("Core Skills", len(core_skills), "skill", "core-skills-modal"),
        _manage_card("Competencies", len(competencies), "item", "competencies-modal"),
        _manage_card("Experience", len(work_history), "role", "work-history-modal"),
        _manage_card("Education", len(education), "entry", "education-modal"),
        _manage_card("Certifications", len(certifications), "certification", "certifications-modal"),
        _manage_card("Tools & Technologies", len(tool_categories), "group", "tools-modal"),
        _manage_card("Languages", len(languages), "language", "languages-modal"),

        Div(
            loading_action_button("Save CV Profile", endpoint="/cv/save", target="#cv-save-result"),
            Span(
                "Live sync enabled" if service_role_is_configured() else "Add the service-role key to enable saving",
                cls="admin-save-note",
            ),
            cls="admin-form-actions mt-4",
        ),
        Div(id="cv-save-result", cls="mt-3"),
        action="/cv/save",
        method="post",
        hx_post="/cv/save",
        hx_target="#cv-save-result",
        hx_swap="innerHTML",
        cls="admin-cv-form",
    )

    insight_panel = Card(
        Div(
            Div(
                Span("Current profile", cls="admin-kicker"),
                H2(meta.name, cls="admin-section-title mb-2"),
                P(meta.summary, cls="admin-module-copy mb-0"),
                cls="admin-detail-copy",
            ),
            Div(
                Badge(summary.source, cls="text-bg-secondary admin-metric-delta"),
                Badge("Live sync on" if service_role_is_configured() else "Setup needed", cls=f"{'text-bg-success' if service_role_is_configured() else 'text-bg-warning'} admin-metric-delta"),
                cls="d-flex flex-wrap gap-2 mt-3",
            ),
            Div(
                Row(
                    Col(
                        Div(
                            H3("Profile Snapshot", cls="admin-subsection-title"),
                            Div(
                                Div(Span("Role", cls="admin-field-label"), Strong(meta.role)),
                                Div(Span("Email", cls="admin-field-label"), Strong(meta.email)),
                                Div(Span("Phone", cls="admin-field-label"), Strong(meta.phone)),
                                Div(Span("Location", cls="admin-field-label"), Strong(meta.location)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                    ),
                    Col(
                        Div(
                            H3("Profile Links", cls="admin-subsection-title"),
                            Div(
                                Div(Span("GitHub", cls="admin-field-label"), Strong(meta.github)),
                                Div(Span("LinkedIn", cls="admin-field-label"), Strong(meta.linkedin, cls="text-wrap-wrap")),
                                Div(Span("WhatsApp", cls="admin-field-label"), Strong(meta.whatsapp)),
                                cls="admin-field-grid",
                            ),
                            cls="admin-detail-block",
                        ),
                        span=12,
                        md=6,
                        cls="mt-4 mt-md-0",
                    ),
                    cls="g-4 mt-1",
                ),
                cls="mt-4",
            ),
            Div(
                H3("CV Editor", cls="admin-subsection-title"),
                P("Update the profile, skills, experience, education, certifications, tools, and languages that power both the interactive CV and the branded download.", cls="admin-module-copy"),
                editor_form,
                # Section management modals (render after editor_form so they work with Bootstrap JS)
                _simple_item_modal("core-skills-modal", "Core Skills", core_skills,
                    "/cv/section/core_skills/save", "Skill",
                    "Manage core skills. Add, edit, or remove individual skills.", "cs-template", _TEMPLATES["cs"]),
                _simple_item_modal("competencies-modal", "Competencies", competencies,
                    "/cv/section/competencies/save", "Competency",
                    "Manage competencies. Add, edit, or remove individual competencies.", "cp-template", _TEMPLATES["cp"]),
                _work_history_modal(work_history),
                _education_modal(education),
                _certifications_modal(certifications),
                _tools_modal(tool_categories),
                _languages_modal(languages),
                _TEMPLATE_BLOCK,
                cls="admin-detail-block mt-4",
            ),
            cls="admin-panel-stack",
        ),
        cls="admin-surface-card h-100",
    )

    reference_panels = Row(
        Col(
            _stack_panel(
                "Experience",
                [f"{item.title} | {item.organisation} | {item.period}" for item in work_history],
            ),
            span=12,
            lg=6,
            cls="d-none d-lg-block",
        ),
        Col(
            _stack_panel(
                "Education & Certifications",
                [f"{item.degree} | {item.institution}" for item in education] + [f"{item.name} | {item.issuer}" for item in certifications],
            ),
            span=12,
            lg=6,
            cls="mt-4 mt-lg-0 d-lg-block",
        ),
        cls="g-4",
    )
    reference_panels_two = Row(
        Col(
            _stack_panel(
                "Tools & Technologies",
                [f"{item.label}: {', '.join(item.tools[:4])}" for item in tool_categories],
            ),
            span=12,
            lg=6,
            cls="d-lg-block",
        ),
        Col(
            _stack_panel(
                "Languages",
                [f"{label} | {level} | {score}%" for label, level, score in languages],
            ),
            span=12,
            lg=6,
            cls="mt-4 mt-lg-0 d-lg-block",
        ),
        cls="g-4 mt-1",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | CV Content",
            description="CV content workspace for managing the structured resume profile and brand-facing details.",
            url=f"{settings.base_url}/cv",
        ),
        *page_frame(
            Row(
                summary_card("Work Items", str(summary.work_items), "Current experience entries in the structured CV timeline."),
                summary_card("Certifications", str(summary.certifications), "Current credential entries in the structured CV data."),
                summary_card("Tool Groups", str(summary.tool_groups), f"Live source: {summary.source}."),
                cls="g-4",
            ),
            SectionWrap(
                "CV Workspace",
                Row(
                    Col(insight_panel, span=12, lg=7),
                    Col(
                        Div(reference_panels, reference_panels_two, cls="admin-cv-side-stack"),
                        span=12,
                        lg=5,
                        cls="mt-4 mt-lg-0",
                    ),
                    cls="g-4",
                ),
            ),
            current="/cv",
            title="CV Content",
        ),
    )
