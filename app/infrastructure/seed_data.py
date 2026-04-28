"""Static dashboard copy for the admin overview shell."""

from __future__ import annotations

from app.domain.models import ActivityItem, AdminMetric, AdminModule

METRICS = (
    AdminMetric("Published Projects", "12", "Projects workspace is now live", "info"),
    AdminMetric("Blog Posts", "4", "+1 draft in progress", "success"),
    AdminMetric("CV Sections", "7", "All synced", "primary"),
    AdminMetric("Client Pipeline", "Live", "Proposals, quotes, and invoices now share one workflow", "warning"),
    AdminMetric("Media Library", "Ready", "Upload once and reuse asset URLs everywhere", "info"),
)

MODULES = (
    AdminModule(
        "Projects",
        "Manage case studies, featured flags, tech stacks, and project media.",
        "/projects",
        "12 items",
        "kanban",
    ),
    AdminModule(
        "Blog",
        "Create articles, maintain metadata, and control published visibility.",
        "/blog",
        "4 posts",
        "journal-richtext",
    ),
    AdminModule(
        "CV Content",
        "Update your CV summary, experience, certifications, and downloadable resume data.",
        "/cv",
        "7 sections",
        "file-earmark-person",
    ),
    AdminModule(
        "Submissions",
        "Review contact messages, booking requests, and future CRM-style follow-up states.",
        "/submissions",
        "Live inbox",
        "inbox",
    ),
    AdminModule(
        "Deals",
        "Draft proposals, quick quotes, and invoices as connected stages of the same client deal.",
        "/deals",
        "Pipeline live",
        "briefcase",
    ),
    AdminModule(
        "Media",
        "Upload reusable images and documents to Supabase Storage, then reuse the generated public URLs across the site.",
        "/media",
        "Storage-ready",
        "images",
    ),
    AdminModule(
        "Site Settings",
        "Control profile details, links, defaults, and publishing preferences.",
        "/settings",
        "Live profile",
        "sliders",
    ),
)

ACTIVITY = (
    ActivityItem("Blog workflow", "FastHTML + Faststrap article is ready for editorial review.", "Draft"),
    ActivityItem("CV content", "Branded PDF and interactive CV now read from the same structured data.", "Stable"),
    ActivityItem("Forms", "Contact and booking now write into Supabase, with graceful WhatsApp/email fallback if delivery is unavailable.", "Live"),
    ActivityItem("Projects workspace", "Project records are now fully managed from a live admin workspace that stays in sync with the portfolio.", "Live"),
    ActivityItem("Blog workspace", "Editorial records now share the same live editing and publishing flow as projects.", "Live"),
    ActivityItem("CV workspace", "Profile, summary, and grouped skill content now power both the interactive CV and branded download.", "Live"),
    ActivityItem("Submissions workspace", "The admin inbox is live and already receiving public-site contact and booking records from Supabase.", "Live"),
    ActivityItem("Deals workspace", "Client proposals, quotes, and invoices now sit inside a single pipeline so commercial documents can progress without re-entry.", "Live"),
    ActivityItem("Media workspace", "Reusable uploads now have a dedicated library so new project and blog visuals no longer depend on manual asset hosting.", "Live"),
    ActivityItem("Settings workspace", "Public profile, contact details, links, and SEO defaults now have a dedicated admin editor.", "Live"),
    ActivityItem("Next phase", "The remaining work is deployment, visual QA, and any final schema refinements before ongoing content management.", "Ready"),
)
