"""Deal detail edit tab module — form management, section editor, payment terms, and deletion."""

from __future__ import annotations

from fasthtml.common import A, Button, Div, Form, H2, Input, Label, P, Script, Span, Textarea
from faststrap import Badge, Card, Col, EmptyState, Fx, Icon, Modal, Row, SEO, Spinner

from app.config import settings
from app.domain.deal_content import parse_document_sections
from app.domain.models import AdminDeal
from app.infrastructure.deal_repository import get_deal_with_documents
from app.infrastructure.payment_account_repository import list_payment_accounts
from app.presentation.page_helpers import floating_field, loading_action_button, textarea_field, toggle_pill_group
from app.presentation.pages.deal_helpers import (
    _deal_snapshot_card,
    _document_options,
    _document_status_options,
    _money,
    _stage_options,
    _status_color,
    _workflow_pipeline,
)
from app.presentation.shell import page_frame


def _section_items_list(sections: list) -> list:
    """Render section list items for initial load."""
    items = []
    for i, s in enumerate(sections):
        title = s.get("title", f"Section {i+1}")
        order = s.get("order", i + 1)
        items.append(
            Div(
                Span(f"#{order}", cls="badge bg-secondary me-2", style="font-size:0.7rem;"),
                Span(title, cls="fw-semibold", style="flex:1;"),
                Button(
                    "Edit",
                    type="button",
                    cls="btn btn-sm btn-outline-primary",
                    style="font-size:0.75rem; padding:0.2rem 0.5rem;",
                    onclick=f"editSection({i})",
                ),
                Button(
                    "Del",
                    type="button",
                    cls="btn btn-sm btn-outline-danger",
                    style="font-size:0.75rem; padding:0.2rem 0.5rem;",
                    onclick=f"removeSection({i})",
                ),
                cls="d-flex align-items-center gap-2 py-2 border-bottom",
            )
        )
    if not items:
        items = [P("No sections yet. Add your first section below.", cls="text-muted small mb-0")]
    return items


def _section_manager(selected: AdminDeal) -> Div:
    """Section Manager — add, edit, remove, reorder document sections."""
    sections = parse_document_sections(selected.sections_json)

    section_modal = Modal(
        Div(
            Div(
                Label("Section Title", cls="form-label fw-semibold"),
                Input(
                    type="text",
                    id="section-title-input",
                    cls="form-control",
                    placeholder="e.g. Technical Approach, Timeline, Deliverables...",
                ),
                cls="mb-3",
            ),
            Div(
                Label("Content (Markdown)", cls="form-label fw-semibold"),
                Textarea(
                    id="section-content-input",
                    rows=10,
                    cls="form-control",
                    placeholder=(
                        "Write your section content here. Markdown is supported.\n\n## Subheading\n- List item 1\n-"
                        " List item 2\n\n> Blockquote text"
                    ),
                ),
                P("Supports markdown: headings, lists, bold, italic, tables, code blocks.", cls="form-text text-muted small"),
                cls="mb-3",
            ),
            Input(type="hidden", id="section-edit-index", value="-1"),
            footer=Div(
                Button("Cancel", type="button", cls="btn btn-secondary", **{"data_bs_dismiss": "modal"}),
                Button("Save Section", type="button", cls="btn btn-primary", id="section-save-btn", onclick="saveSection()"),
                cls="d-flex gap-2 justify-content-end",
            ),
        ),
        modal_id="sectionEditModal",
        title="Add Section",
        centered=True,
        size="lg",
    )

    section_js = Script("""
        function getSections() {
            var field = document.getElementById('sections-json-field');
            try { return JSON.parse(field.value || '[]'); } catch(e) { return []; }
        }
        function setSections(sections) {
            document.getElementById('sections-json-field').value = JSON.stringify(sections);
            renderSectionList();
        }
        function renderSectionList() {
            var sections = getSections();
            var container = document.getElementById('section-list-container');
            if (!sections.length) {
                container.innerHTML = '<p class="text-muted small mb-0">No sections yet. Add your first section below.</p>';
                return;
            }
            var html = '';
            for (var i = 0; i < sections.length; i++) {
                var s = sections[i];
                html += '<div class="d-flex align-items-center gap-2 py-2 border-bottom">';
                html += '<span class="badge bg-secondary" style="font-size:0.7rem;">#' + (s.order || (i+1)) + '</span>';
                html += '<span class="fw-semibold" style="flex:1;">' + (s.title || 'Untitled') + '</span>';
                html += '<button type="button" class="btn btn-sm btn-outline-primary" style="font-size:0.75rem;padding:0.2rem 0.5rem;" onclick="editSection(' + i + ')">Edit</button>';
                html += '<button type="button" class="btn btn-sm btn-outline-danger" style="font-size:0.75rem;padding:0.2rem 0.5rem;" onclick="removeSection(' + i + ')">Del</button>';
                html += '</div>';
            }
            container.innerHTML = html;
        }
        function addSection() {
            document.getElementById('section-title-input').value = '';
            document.getElementById('section-content-input').value = '';
            document.getElementById('section-edit-index').value = '-1';
            document.querySelector('#sectionEditModal .modal-title').textContent = 'Add Section';
            var m = new bootstrap.Modal(document.getElementById('sectionEditModal'));
            m.show();
        }
        function editSection(idx) {
            var sections = getSections();
            if (idx < 0 || idx >= sections.length) return;
            document.getElementById('section-title-input').value = sections[idx].title || '';
            document.getElementById('section-content-input').value = sections[idx].content || '';
            document.getElementById('section-edit-index').value = idx;
            document.querySelector('#sectionEditModal .modal-title').textContent = 'Edit Section';
            var m = new bootstrap.Modal(document.getElementById('sectionEditModal'));
            m.show();
        }
        function removeSection(idx) {
            showConfirm(
                'Remove this section?',
                function() {
                    var sections = getSections();
                    sections.splice(idx, 1);
                    for (var i = 0; i < sections.length; i++) sections[i].order = i + 1;
                    setSections(sections);
                },
                null,
                { title: "Remove Section", confirmText: "Remove", variant: "danger" }
            );
        }
        function saveSection() {
            var title = document.getElementById('section-title-input').value.trim();
            var content = document.getElementById('section-content-input').value.trim();
            var idx = parseInt(document.getElementById('section-edit-index').value);
            if (!title) {
                var tc = document.getElementById('toast-container');
                if (tc) {
                    var te = document.createElement('div');
                    te.className = 'toast align-items-center text-bg-warning border-0';
                    te.setAttribute('role', 'alert');
                    te.innerHTML = '<div class="d-flex"><div class="toast-body">Section title is required.</div><button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button></div>';
                    tc.appendChild(te);
                    var bt = new bootstrap.Toast(te, {delay: 4000});
                    bt.show();
                    te.addEventListener('hidden.bs.toast', function(){te.remove();});
                }
                document.getElementById('section-title-input').focus();
                return;
            }
            var sections = getSections();
            if (idx >= 0 && idx < sections.length) {
                sections[idx].title = title;
                sections[idx].content = content;
            } else {
                sections.push({ order: sections.length + 1, title: title, content: content });
            }
            setSections(sections);
            var modal = bootstrap.Modal.getInstance(document.getElementById('sectionEditModal'));
            if (modal) modal.hide();
        }
        document.addEventListener('DOMContentLoaded', function() { renderSectionList(); });
    """)

    return Div(
        Div(
            P("Document Sections", cls="admin-form-section-title"),
            P(
                "Add and manage narrative sections for the proposal. These render as markdown on the client portal.",
                cls="admin-module-copy mb-3 small",
            ),
            Div(id="section-list-container", *_section_items_list(sections)),
            Div(
                Button(
                    "+ Add Section",
                    type="button",
                    cls="btn btn-outline-primary btn-sm",
                    style="font-size:0.82rem;",
                    onclick="addSection()",
                ),
                cls="mt-3",
            ),
            cls="admin-form-section",
        ),
        section_modal,
        section_js,
    )


def _edit_tab(selected: AdminDeal) -> Div:
    """Edit tab — deal settings form refactored from the old editor."""
    accounts = list_payment_accounts()
    return Form(
        Input(type="hidden", name="deal_id", value=selected.deal_id),
        # Client Info
        Div(
            P("Client Info", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Client Name", "client_name", selected.client_name, placeholder="Client name", required=True), span=12, md=6),
                Col(floating_field("Client Email", "client_email", selected.client_email, input_type="email", placeholder="client@example.com", required=True), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Row(
                Col(floating_field("Client Phone", "client_phone", selected.client_phone, placeholder="+234..."), span=12, md=6),
                Col(floating_field("Company", "company", selected.company, placeholder="Client company"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-3",
            ),
            cls="admin-form-section",
        ),
        # Project Brief
        Div(
            P("Project Brief", cls="admin-form-section-title"),
            Row(
                Col(floating_field("Project Title", "project_title", selected.project_title, placeholder="Project title", required=True), span=12, md=7),
                Col(floating_field("Service Type", "service_type", selected.service_type, placeholder="custom-saas, quick-build"), span=12, md=5, cls="mt-3 mt-md-0"),
                cls="g-3",
            ),
            Div(
                Label("Pipeline Stage", cls="admin-form-label"),
                toggle_pill_group("stage", _stage_options(), selected_value=selected.stage),
                cls="admin-form-group mt-3",
            ),
            cls="admin-form-section",
        ),
        # Document Settings
        Div(
            P("Document Settings", cls="admin-form-section-title"),
            Div(
                Label("Document Type", cls="admin-form-label"),
                toggle_pill_group(
                    "document_kind",
                    _document_options(),
                    selected_value=selected.latest_document.kind if selected.latest_document else "proposal",
                ),
                cls="admin-form-group",
            ),
            Div(
                Label("Document Status", cls="admin-form-label"),
                toggle_pill_group(
                    "document_status",
                    _document_status_options(),
                    selected_value=selected.latest_document.status if selected.latest_document else "draft",
                ),
                cls="admin-form-group mt-3",
            ),
            floating_field(
                "Document Title",
                "document_title",
                selected.latest_document.title if selected.latest_document else "",
                placeholder="Proposal for Project X",
                required=True,
            ),
            Row(
                Col(
                    floating_field(
                        "Valid Until",
                        "valid_until",
                        selected.latest_document.valid_until if selected.latest_document else "",
                        input_type="date",
                    ),
                    span=12, md=6,
                ),
                Col(
                    floating_field(
                        "Due Date",
                        "due_date",
                        selected.latest_document.due_date if selected.latest_document else "",
                        input_type="date",
                    ),
                    span=12, md=6, cls="mt-3 mt-md-0",
                ),
                cls="g-3 mt-3",
            ),
            cls="admin-form-section",
        ),
        # Financials
        Div(
            P("Financials", cls="admin-form-section-title"),
            textarea_field(
                "Payment Terms",
                "payment_terms",
                selected.payment_terms,
                rows=4,
                placeholder="Deposit expectations, milestone payments...",
            ),
            Row(
                Col(floating_field("Amount (\u20a6)", "amount_ngn", str(selected.amount_ngn), input_type="number", placeholder="850000"), span=12, md=6),
                Col(floating_field("Deposit %", "deposit_percent", str(selected.deposit_percent), input_type="number", placeholder="50"), span=12, md=6, cls="mt-3 mt-md-0"),
                cls="g-3 mt-1",
            ),
            cls="admin-form-section",
        ),
        # Document Sections
        _section_manager(selected),
        # Hidden fields for backward compat
        Input(type="hidden", name="summary", value=selected.summary),
        Input(type="hidden", name="background_text", value=selected.background_text),
        Input(type="hidden", name="scope_notes", value=selected.scope_notes),
        Input(type="hidden", name="option_notes_text", value=selected.option_notes_text),
        Input(type="hidden", name="tech_stack", value=", ".join(selected.tech_stack)),
        Input(type="hidden", name="timeline_text", value=selected.timeline_text),
        Input(type="hidden", name="exclusions_text", value=selected.exclusions_text),
        Input(type="hidden", name="closing_note", value=selected.closing_note),
        Input(type="hidden", name="sections_json", value=selected.sections_json, id="sections-json-field"),
        Input(type="hidden", name="line_items", value=selected.line_items_text),
        Div(
            loading_action_button("Save Changes", endpoint="/deals/save", target="#deal-edit-result"),
            cls="admin-form-actions mt-4",
        ),
        Button(
            "Delete Deal",
            type="button",
            cls="btn btn-outline-danger mt-2",
            hx_post="/deals/delete",
            hx_vals=f'{{"deal_id": "{selected.deal_id}"}}',
            hx_target="#deal-edit-result",
            hx_swap="innerHTML",
            hx_confirm="Are you sure you want to permanently delete this deal and all its documents?",
        ),
        Div(id="deal-edit-result", cls="mt-3"),
        action="/deals/save",
        method="post",
        hx_post="/deals/save",
        hx_target="#deal-edit-result",
        hx_swap="innerHTML",
        cls="admin-settings-form",
    )


def deal_edit_page(*, deal_id: str = "", view: str = "edit") -> tuple:
    """Deal edit tab page layout."""
    selected = get_deal_with_documents(deal_id) if deal_id else None
    if not selected:
        return (
            *SEO(
                title=f"{settings.app_name} | Deal Not Found",
                description="Deal not found.",
                url=f"{settings.base_url}/deals",
            ),
            *page_frame(
                EmptyState(
                    icon="exclamation-circle",
                    title="Deal not found",
                    description="The deal you're looking for doesn't exist or has been deleted.",
                    cls="py-5",
                ),
                current="/deals",
                title="Deal Not Found",
            ),
        )

    def _nav_pill(label: str, target_view: str) -> A:
        pill_href = f"/deals/{deal_id}?view={target_view}"
        return A(
            label,
            href=pill_href,
            hx_get=pill_href,
            hx_target="body",
            hx_swap="innerHTML",
            hx_push_url="true",
            cls=f"admin-filter-chip{' active' if view == target_view else ''}",
        )

    nav_pills = Div(
        _nav_pill("Overview", "overview"),
        _nav_pill("Documents", "documents"),
        _nav_pill("Edit", "edit"),
        cls="d-flex flex-wrap gap-2 mb-4",
    )

    back_link = A(
        Icon("arrow-left", cls="me-2"),
        "Back to Pipeline",
        Spinner(size="sm", cls="admin-back-spinner ms-2"),
        href="/deals",
        hx_get="/deals",
        hx_target="body",
        hx_swap="innerHTML",
        hx_push_url="true",
        hx_indicator="#deal-back-link",
        id="deal-back-link",
        cls="admin-back-link mb-3",
    )

    return (
        *SEO(
            title=f"{settings.app_name} | {selected.project_title} - Edit",
            description=f"Edit deal settings for {selected.project_title}",
            url=f"{settings.base_url}/deals/{deal_id}",
        ),
        *page_frame(
            back_link,
            Div(
                Div(
                    H2(selected.project_title, cls="admin-section-title mb-1"),
                    Div(
                        Span(selected.client_name, cls="admin-project-meta"),
                        Badge(
                            selected.stage.replace("_", " ").title(),
                            cls=f"bg-{_status_color(selected.stage)} bg-opacity-10 text-{_status_color(selected.stage)} ms-2",
                        ),
                        Span(_money(selected.amount_ngn), cls="admin-project-meta ms-2"),
                        cls="d-flex align-items-center gap-2 flex-wrap",
                    ),
                ),
                _workflow_pipeline(selected),
                cls="mb-4",
            ),
            nav_pills,
            Row(
                Col(_deal_snapshot_card(selected), span=12, lg=4),
                Col(
                    Card(
                        _edit_tab(selected),
                        cls=[Fx.base, Fx.fade_in, "admin-surface-card h-100"],
                    ),
                    span=12, lg=8, cls="mt-4 mt-lg-0",
                ),
                cls="g-4",
            ),
            current="/deals",
            title=selected.project_title,
        ),
    )
