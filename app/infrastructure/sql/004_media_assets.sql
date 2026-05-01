insert into storage.buckets (id, name, public)
values ('portfolio-media', 'portfolio-media', true)
on conflict (id) do nothing;

create table if not exists public.media_assets (
    id uuid primary key default gen_random_uuid(),
    title text not null,
    asset_kind text not null default 'image'
        check (asset_kind in ('image', 'document', 'logo', 'resume', 'other')),
    alt_text text not null default '',
    bucket_name text not null default 'portfolio-media',
    storage_path text not null unique,
    public_url text not null,
    content_type text not null default 'application/octet-stream',
    size_bytes integer not null default 0,
    created_at timestamptz not null default now()
);

alter table public.media_assets enable row level security;

drop policy if exists "Service role manages media assets" on public.media_assets;
create policy "Service role manages media assets"
on public.media_assets
for all
to service_role
using (true)
with check (true);

drop policy if exists "Public can read portfolio media objects" on storage.objects;
create policy "Public can read portfolio media objects"
on storage.objects
for select
to anon, authenticated
using (bucket_id = 'portfolio-media');

drop policy if exists "Service role manages portfolio media objects" on storage.objects;
create policy "Service role manages portfolio media objects"
on storage.objects
for all
to service_role
using (bucket_id = 'portfolio-media')
with check (bucket_id = 'portfolio-media');
