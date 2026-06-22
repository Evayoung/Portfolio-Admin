create table if not exists public.admin_audit_logs (
    id uuid primary key default gen_random_uuid(),
    action text not null,
    target_type text not null default '',
    target_id text not null default '',
    actor_email text not null default '',
    detail text not null default '',
    created_at timestamptz not null default now()
);

alter table public.admin_audit_logs enable row level security;

drop policy if exists "Service role manages admin audit logs" on public.admin_audit_logs;
create policy "Service role manages admin audit logs"
on public.admin_audit_logs
for all
to service_role
using (true)
with check (true);

alter table public.media_assets
add column if not exists updated_at timestamptz not null default now();

drop trigger if exists set_media_assets_updated_at on public.media_assets;
create trigger set_media_assets_updated_at
before update on public.media_assets
for each row execute function public.set_updated_at();

alter table public.client_documents
add column if not exists revoked_at timestamptz,
add column if not exists version_number integer not null default 1,
add column if not exists last_sent_at timestamptz;
