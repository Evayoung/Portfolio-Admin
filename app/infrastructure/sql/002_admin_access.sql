create table if not exists public.admin_access (
  id uuid primary key default gen_random_uuid(),
  login_email text not null unique,
  password_hash text not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create trigger set_admin_access_updated_at
before update on public.admin_access
for each row
execute function public.set_updated_at();

alter table public.admin_access enable row level security;

drop policy if exists "Public read admin access disabled" on public.admin_access;
create policy "Public read admin access disabled"
on public.admin_access
for select
to anon, authenticated
using (false);

drop policy if exists "Service role manages admin access" on public.admin_access;
create policy "Service role manages admin access"
on public.admin_access
for all
to service_role
using (true)
with check (true);
