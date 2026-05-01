-- Neo Admin production hardening migration.
-- Run this after 001_initial_schema.sql through 005_document_links_and_accounts.sql
-- if your Supabase project already has the earlier schema.

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create unique index if not exists idx_client_documents_public_token
on public.client_documents (public_token)
where public_token <> '';

create index if not exists idx_client_deals_stage_updated
on public.client_deals (stage, updated_at desc);

create index if not exists idx_client_documents_deal_kind
on public.client_documents (deal_id, kind, updated_at desc);

drop trigger if exists set_client_deals_updated_at on public.client_deals;
create trigger set_client_deals_updated_at
before update on public.client_deals
for each row execute function public.set_updated_at();

drop trigger if exists set_client_documents_updated_at on public.client_documents;
create trigger set_client_documents_updated_at
before update on public.client_documents
for each row execute function public.set_updated_at();

alter table public.client_deals enable row level security;
alter table public.client_documents enable row level security;

drop policy if exists "Service role manages client deals" on public.client_deals;
create policy "Service role manages client deals"
on public.client_deals
for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role manages client documents" on public.client_documents;
create policy "Service role manages client documents"
on public.client_documents
for all
to service_role
using (true)
with check (true);

insert into storage.buckets (id, name, public)
values ('portfolio-media', 'portfolio-media', true)
on conflict (id) do nothing;

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

create unique index if not exists idx_payment_accounts_single_default
on public.payment_accounts (is_default)
where is_default = true;

create index if not exists idx_client_document_responses_document_created
on public.client_document_responses (document_id, created_at desc);

alter table public.payment_accounts enable row level security;
alter table public.client_document_responses enable row level security;

drop policy if exists "Service role manages payment accounts" on public.payment_accounts;
create policy "Service role manages payment accounts"
on public.payment_accounts
for all
to service_role
using (true)
with check (true);

drop policy if exists "Service role manages document responses" on public.client_document_responses;
create policy "Service role manages document responses"
on public.client_document_responses
for all
to service_role
using (true)
with check (true);
