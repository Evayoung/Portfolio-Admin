"""CV workspace for Neo Admin — split into interactive preview and dedicated editor."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, H3, H4, Input, Li, P, Span, Strong, Textarea, Ul
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Modal, Progress, Row, SEO, Spinner, StatusBadge

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
            Button("×", type="button", cls="btn admin-danger-btn btn-sm flex-shrink-0",
                   onclick="removeCvItem(this)", aria_label="Remove item", style="height:2.4rem;"),
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
                Div(Button("×", type="button", cls="btn admin-danger-btn btn-sm flex-shrink-0",
                           onclick="removeCvItem(this)", aria_label="Remove entry"), cls="col-md-2 d-flex align-items-end"),
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
            Div(Button("×", type="button", cls="btn admin-danger-btn btn-sm",
                       onclick="removeCvItem(this)", aria_label="Remove entry"), cls="col-md-2 d-flex align-items-end"),
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
            Div(Button("×", type="button", cls="btn admin-danger-btn btn-sm",
                       onclick="removeCvItem(this)", aria_label="Remove certification"), cls="col-md-1 d-flex align-items-end"),
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
            Div(Button("×", type="button", cls="btn admin-danger-btn btn-sm",
                       onclick="removeCvItem(this)", aria_label="Remove tool group"), cls="col-md-2 d-flex align-items-end"),
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
            Div(Button("×", type="button", cls="btn admin-danger-btn btn-sm",
                       onclick="removeCvItem(this)", aria_label="Remove language"), cls="col-md-2 d-flex align-items-end"),
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


# ── Preview helpers ──

def _work_item_preview(item) -> Div:
    """Render a single work history entry in the CV preview — mirrors public cv_page.py."""
    return Div(
        Div(
            Div(cls="cv-timeline-dot"),
            cls="cv-timeline-track",
        ),
        Div(
            Div(
                Div(
                    H3(item.title, cls="cv-role-title"),
                    Span(item.period, cls="cv-period-pill"),
                    cls="d-flex justify-content-between align-items-start flex-wrap gap-2",
                ),
                Div(
                    Icon("building", cls="me-1 small"),
                    Strong(item.organisation),
                    Span(" | ", cls="text-muted"),
                    Span(item.location, cls="text-muted small"),
                    cls="cv-org-line mt-1",
                ),
                Ul(
                    *[Li(bullet, cls="cv-bullet") for bullet in item.bullets],
                    cls="cv-bullet-list mt-3",
                ),
                cls="cv-work-body",
            ),
            cls="cv-work-content",
        ),
        cls="cv-timeline-entry",
    )


def _tool_category_preview(cat) -> Div:
    """Render a single tool category block in the CV preview — mirrors public cv_page.py."""
    return Div(
        H4(cat.label, cls="cv-tool-category"),
        Div(
            *[Span(tool, cls="cv-tool-badge") for tool in cat.tools],
            cls="cv-tool-pills",
        ),
        cls="cv-tool-block",
    )


# ── Page functions ──

def cv_preview_page() -> tuple:
    meta = get_cv_meta()
    summary = get_cv_workspace_summary()
    work_history = list_work_history()
    education = list_education()
    certifications = list_certifications()
    tool_categories = list_tool_categories()
    languages = list_languages()
    core_skills = list_core_skills()
    competencies = list_competencies()

    # ── Action bar ──
    action_bar = Div(
        Div(
            A(
                Icon("pencil", cls="me-2"),
                "Edit CV",
                Spinner(size="sm", cls="admin-back-spinner ms-2"),
                href="/cv/edit",
                hx_get="/cv/edit",
                hx_target="body",
                hx_swap="innerHTML",
                hx_push_url="true",
                hx_indicator="#cv-edit-btn",
                id="cv-edit-btn",
                cls="btn admin-module-btn",
            ),
            A(
                Icon("download", cls="me-2"),
                "Download PDF",
                href="/resume/download/pdf",
                target="_blank",
                cls="btn admin-muted-btn",
            ),
            cls="d-flex align-items-center gap-3",
        ),
        cls="d-flex justify-content-between align-items-center mb-4",
    )

    # ── CV Preview Card — mirrors public portfolio layout ──
    preview_card = Card(
        Div(
            # Header band
            Div(
                H2(meta.name, cls="admin-section-title mb-1"),
                P(meta.role, cls="admin-module-copy text-muted mb-3"),
                Div(
                    Span(Icon("geo-alt", cls="me-1"), meta.location, cls="cv-contact-chip"),
                    Span(Icon("telephone", cls="me-1"), meta.phone, cls="cv-contact-chip"),
                    Span(Icon("envelope", cls="me-1"), meta.email, cls="cv-contact-chip"),
                    A(Span(Icon("github", cls="me-1"), "GitHub", cls="cv-contact-chip"),
                      href=meta.github, target="_blank", cls="cv-contact-link"),
                    A(Span(Icon("linkedin", cls="me-1"), "LinkedIn", cls="cv-contact-chip"),
                      href=meta.linkedin, target="_blank", cls="cv-contact-link"),
                    cls="cv-contact-grid mt-2 mb-0",
                ),
                cls="admin-detail-block p-4 mb-4",
            ),
            # Body: main column + sidebar
            Row(
                # Left — main CV content (lg=8)
                Col(
                    # Professional Summary
                    Div(
                        H3("Professional Summary", cls="admin-subsection-title mb-2"),
                        P(meta.summary, cls="admin-module-copy"),
                        cls="admin-detail-block p-3 mb-4",
                    ),
                    # Work History
                    Div(
                        H3("Experience", cls="admin-subsection-title mb-3"),
                        Div(
                            *[_work_item_preview(item) for item in work_history],
                            cls="cv-timeline",
                        ),
                        cls="mb-4",
                    ),
                    # Education + Certs row
                    Row(
                        Col(
                            Div(
                                H3("Education", cls="admin-subsection-title mb-3"),
                                Div(
                                    *[
                                        Div(
                                            Div(cls="cv-timeline-dot cv-timeline-dot-edu"),
                                            Div(
                                                H4(edu.degree, cls="cv-role-title"),
                                                P(edu.institution, cls="cv-org-line"),
                                                Span(edu.period, cls="cv-period-pill"),
                                                P(edu.note, cls="cv-edu-note mt-2") if edu.note else "",
                                                cls="cv-work-body",
                                            ),
                                            cls="cv-timeline-entry",
                                        )
                                        for edu in education
                                    ],
                                    cls="cv-timeline",
                                ),
                                cls="mb-4",
                            ),
                            Div(
                                H3("Certifications", cls="admin-subsection-title mb-3"),
                                Div(
                                    *[
                                        Div(
                                            Div(Icon("award", cls="cv-cert-icon"), cls="cv-cert-icon-box"),
                                            Div(
                                                Strong(cert.name),
                                                P(f"{cert.issuer} | {cert.year}", cls="small text-muted mb-0"),
                                            ),
                                            cls="cv-cert-row",
                                        )
                                        for cert in certifications
                                    ],
                                    cls="cv-cert-list",
                                ),
                            ),
                            span=12, lg=7,
                        ),
                        Col(
                            Div(
                                H3("Tools & Technologies", cls="admin-subsection-title mb-3"),
                                Div(
                                    *[_tool_category_preview(cat) for cat in tool_categories],
                                    cls="cv-tools-grid",
                                ),
                            ),
                            span=12, lg=5, cls="mt-4 mt-lg-0",
                        ),
                        cls="g-4",
                    ),
                    span=12, lg=8,
                ),
                # Right sidebar (lg=4)
                Col(
                    Div(
                        # Core Skills
                        Card(
                            H3("Core Skills", cls="cv-sidebar-title"),
                            Ul(
                                *[Li(skill, cls="cv-skill-item") for skill in core_skills],
                                cls="cv-skill-list",
                            ),
                            cls="cv-sidebar-card mb-4",
                        ),
                        # Competencies
                        Card(
                            H3("Competencies", cls="cv-sidebar-title"),
                            Div(
                                *[Badge(c, variant="secondary", cls="me-1 mb-1") for c in competencies],
                                cls="d-flex flex-wrap gap-1",
                            ),
                            cls="cv-sidebar-card mb-4",
                        ),
                        # Languages with Progress bars
                        Card(
                            H3("Languages", cls="cv-sidebar-title"),
                            *[
                                Div(
                                    Div(
                                        Span(lang, cls="fw-semibold small"),
                                        Span(level, cls="small text-muted"),
                                        cls="d-flex justify-content-between mb-1",
                                    ),
                                    Progress(value=pct, variant="info", height="8px"),
                                    cls="mb-3",
                                )
                                for lang, level, pct in languages
                            ],
                            cls="cv-sidebar-card",
                        ),
                        cls="cv-sidebar",
                    ),
                    span=12, lg=4, cls="mt-4 mt-lg-0",
                ),
                cls="g-4",
            ),
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    return (
        *SEO(
            title=f"{settings.app_name} | CV Preview",
            description="Interactive CV preview — live admin view of the structured resume profile.",
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
                "CV Preview",
                Div(action_bar, preview_card),
            ),
            current="/cv",
            title="CV Preview",
        ),
    )


def cv_edit_page() -> tuple:
    """Dedicated CV editor page \u2014 two-column layout: snapshot card (lg=5) + editor form (lg=7).
    All 7 section modals are rendered at page_frame() root to avoid z-index stacking context issues.
    """
    meta = get_cv_meta()
    summary = get_cv_workspace_summary()
    work_history = list_work_history()
    education = list_education()
    certifications = list_certifications()
    tool_categories = list_tool_categories()
    languages = list_languages()
    core_skills = list_core_skills()
    competencies = list_competencies()

    # ── HTMX back-link with Faststrap Spinner (Pattern 2) ──
    back_link = A(
        Icon("arrow-left", cls="me-2"),
        "Back to CV Preview",
        Spinner(size="sm", cls="admin-back-spinner ms-2"),
        href="/cv",
        hx_get="/cv",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        hx_indicator="#cv-back-link",
        id="cv-back-link",
        cls="admin-back-link mb-3",
    )

    # ── CV Snapshot Hero Card (Left Column lg=5 — Pattern 7) ──
    snapshot_card = Card(
        Div(
            H3(meta.name, cls="admin-section-title mb-1"),
            P(meta.role, cls="admin-module-copy text-muted mb-4"),
            # Contact block
            Div(
                H3("Contact", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("Email", cls="admin-field-label"), Strong(meta.email)),
                    Div(Span("Phone", cls="admin-field-label"), Strong(meta.phone)),
                    Div(Span("Location", cls="admin-field-label"), Strong(meta.location)),
                    Div(Span("WhatsApp", cls="admin-field-label"), Strong(meta.whatsapp)),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
                cls="mb-4",
            ),
            # Links block
            Div(
                H3("Links", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("GitHub", cls="admin-field-label"), Strong(meta.github, cls="text-break")),
                    Div(Span("LinkedIn", cls="admin-field-label"), Strong(meta.linkedin, cls="text-break")),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
                cls="mb-4",
            ),
            # Data snapshot block
            Div(
                H3("Data Snapshot", cls="admin-subsection-title mb-2"),
                Div(
                    Div(Span("Experience Roles", cls="admin-field-label"), Strong(str(summary.work_items))),
                    Div(Span("Certifications", cls="admin-field-label"), Strong(str(summary.certifications))),
                    Div(Span("Tool Groups", cls="admin-field-label"), Strong(str(summary.tool_groups))),
                    Div(
                        Span("Sync Status", cls="admin-field-label"),
                        StatusBadge(
                            "Live sync on" if service_role_is_configured() else "Setup needed",
                            status="success" if service_role_is_configured() else "warning",
                            show_dot=True,
                            pill=True,
                            cls="admin-badge-sm ms-2",
                        ),
                    ),
                    cls="admin-field-grid admin-detail-block p-3",
                ),
            ),
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    # ── Editor Form (preserved exactly, modals removed from here) ──
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
        # Section management cards
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

    # ── Editor Form Panel (Right Column lg=7) ──
    form_panel = Card(
        Div(
            H3("CV Editor", cls="admin-subsection-title"),
            P(
                "Update the profile, skills, experience, education, certifications, tools, and languages "
                "that power both the interactive CV and the branded download.",
                cls="admin-module-copy mb-4",
            ),
            editor_form,
            cls="admin-panel-stack",
        ),
        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
    )

    return (
        *SEO(
            title=f"{settings.app_name} | Edit CV",
            description="CV editor — update profile, skills, experience, education, certifications, tools, and languages.",
            url=f"{settings.base_url}/cv/edit",
        ),
        *page_frame(
            back_link,
            Row(
                Col(snapshot_card, span=12, lg=5),
                Col(form_panel, span=12, lg=7, cls="mt-4 mt-lg-0"),
                cls="g-4",
            ),
            # ── All 7 section modals at ROOT level ──
            # Rendered here (not inside any Fx card) to escape CSS transform stacking context.
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
            current="/cv",
            title="Edit CV",
        ),
    )



