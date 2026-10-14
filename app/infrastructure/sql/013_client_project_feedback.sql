-- Private project closeout feedback, collected through unguessable share links.
-- This is separate from public testimonials; publishing requires admin review.

create table if not exists public.client_project_feedback (
    id uuid primary key default gen_random_uuid(),
    deal_id uuid not null unique references public.client_deals(id) on delete cascade,
    public_token text unique,
    reviewer_name text not null default '',
    reviewer_email text not null default '',
    rating smallint check (rating between 1 and 5),
    comments text not null default '',
    testimonial_consent boolean not null default false,
    testimonial_quote text not null default '',
    review_status text not null default 'new' check (review_status in ('new', 'reviewed', 'archived')),
    submitted_at timestamptz,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists idx_client_project_feedback_submitted
on public.client_project_feedback (submitted_at desc nulls last, created_at desc);

drop trigger if exists set_client_project_feedback_updated_at on public.client_project_feedback;
create trigger set_client_project_feedback_updated_at
before update on public.client_project_feedback
for each row execute function public.set_updated_at();

alter table public.client_project_feedback enable row level security;
revoke all on public.client_project_feedback from public, anon, authenticated;
grant all on public.client_project_feedback to service_role;

drop policy if exists "Service role manages client project feedback" on public.client_project_feedback;
create policy "Service role manages client project feedback"
on public.client_project_feedback
for all
to service_role
using (true)
with check (true);
