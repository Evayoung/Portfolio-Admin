"""Shared presentation helpers for Neo Admin pages."""

from __future__ import annotations

from fasthtml.common import Div, H3, Input, P, Span, Textarea
from faststrap import Alert, Button, Card, Col, FilterBar, FloatingLabel, FormGroup, MetricCard, ToggleGroup


_TONE_TO_VARIANT = {
    "success": "success",
    "warning": "warning",
    "danger": "danger",
    "info": "info",
}

_TONE_TO_TREND = {
    "success": "up",
    "danger": "down",
    "warning": "neutral",
    "info": "neutral",
}


def status_alert(title: str, message: str, tone: str = "info") -> Div:
    """Render a shared Faststrap alert for save/update responses."""

    return Alert(
        P(message, cls="mb-0"),
        heading=H3(title, cls="h6 mb-2"),
        variant=_TONE_TO_VARIANT.get(tone, "info"),
        cls="admin-save-alert",
    )


def summary_card(
    label: str,
    value: str,
    note: str,
    *,
    span: int = 12,
    md: int | None = 4,
    lg: int | None = None,
    xl: int | None = None,
) -> Col:
    """Render the shared summary card used across workspace pages."""

    col_kwargs: dict[str, int] = {"span": span}
    if md is not None:
        col_kwargs["md"] = md
    if lg is not None:
        col_kwargs["lg"] = lg
    if xl is not None:
        col_kwargs["xl"] = xl

    return Col(
        Card(
            Div(
                Span(label, cls="admin-metric-label"),
                H3(value, cls="admin-metric-value"),
                P(note, cls="admin-module-copy mb-0"),
                cls="admin-metric-card-body",
            ),
            cls="admin-surface-card h-100",
        ),
        **col_kwargs,
    )


def overview_metric_card(item) -> Col:
    """Render the overview dashboard metric with Faststrap MetricCard."""

    return Col(
        MetricCard(
            item.label,
            item.value,
            delta=item.delta,
            delta_type=_TONE_TO_TREND.get(item.tone, "neutral"),
            cls="admin-surface-card h-100 admin-overview-metric",
        ),
        span=12,
        md=6,
        xl=3,
    )


def search_filter_bar(
    *,
    endpoint: str,
    placeholder: str,
    search_value: str,
    hidden_fields: dict[str, str],
    submit_label: str = "Find",
    form_cls: str = "",
) -> Div:
    """Compose a Faststrap FilterBar for the shared workspace search pattern."""

    hidden_inputs = [
        Input(type="hidden", name=name, value=value)
        for name, value in hidden_fields.items()
    ]
    search_input = Input(
        type="search",
        name="search",
        value=search_value,
        placeholder=placeholder,
        cls="form-control admin-form-control admin-search-input",
    )
    return FilterBar(
        *hidden_inputs,
        Div(search_input, cls="admin-search-field"),
        endpoint=endpoint,
        method="get",
        mode="apply",
        apply_label=submit_label,
        form_cls=form_cls,
        filters_cls="admin-filter-fields",
        actions_cls="admin-filter-actions",
    )


def floating_field(
    label: str,
    name: str,
    value: str = "",
    *,
    input_type: str = "text",
    placeholder: str = "",
    required: bool = False,
    **kwargs,
) -> Div:
    """Shared floating input field for admin forms."""

    return FloatingLabel(
        name,
        label=label,
        input_type=input_type,
        value=value,
        placeholder=placeholder or label,
        required=required,
        input_cls="admin-form-control",
        label_cls="admin-floating-label",
        cls="admin-form-group admin-floating-field",
        **kwargs,
    )


def textarea_field(
    label: str,
    name: str,
    value: str = "",
    *,
    rows: int = 5,
    placeholder: str = "",
    required: bool = False,
) -> Div:
    """Shared textarea field wrapped with Faststrap FormGroup."""

    textarea = Textarea(
        value,
        id=name,
        name=name,
        rows=rows,
        placeholder=placeholder,
        required=required,
        cls="form-control admin-form-control admin-form-textarea",
    )
    return FormGroup(
        textarea,
        label=label,
        required=required,
        cls="admin-form-group",
    )


def toggle_pill_group(
    name: str,
    options: list[tuple[str, str]],
    *,
    selected_value: str,
) -> Div:
    """Shared pill-style single-select group built on Faststrap ToggleGroup."""

    active_index = next(
        (index for index, (value, _label) in enumerate(options) if value == selected_value),
        0,
    )
    return ToggleGroup(
        *[
            Button(
                label,
                type="button",
                variant="link",
                cls="admin-radio-pill",
            )
            for value, label in options
        ],
        name=name,
        values=[value for value, _label in options],
        active_index=active_index,
        cls="admin-radio-grid",
    )
