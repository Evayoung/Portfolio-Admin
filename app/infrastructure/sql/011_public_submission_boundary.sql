-- Public portfolio submission boundary.
-- Review the live schema against 001_initial_schema.sql before applying this
-- migration to staging. Apply in staging first; do not infer live policy state.

-- Remove table-level INSERT inherited from broad Supabase defaults. The public
-- role may insert only visitor-controlled fields; status/source use DB defaults.
alter table public.contact_submissions enable row level security;
alter table public.booking_requests enable row level security;

-- Start from no table-level access for public roles. Explicit column-level
-- grants below then allow only public reads and submission fields needed by
-- the portfolio. service_role is intentionally untouched for Neo Admin.
revoke all privileges on table public.contact_submissions from public, anon, authenticated;
revoke all privileges on table public.booking_requests from public, anon, authenticated;
revoke all privileges on table public.site_settings from public, anon, authenticated;
revoke all privileges on table public.project_tech_stack from public, anon, authenticated;
revoke all privileges on table public.blog_post_tags from public, anon, authenticated;
revoke all privileges on table public.blog_tags from public, anon, authenticated;
revoke all privileges on table public.service_deliverables from public, anon, authenticated;
revoke all privileges on table public.pricing_points from public, anon, authenticated;

-- Remove any old column-level grants too; table-level REVOKE does not clear
-- separately granted column privileges. This keeps the migration safe when
-- applied over the broad default grants reported by the staging preflight.
do $$
declare
  target record;
  column_privilege text;
begin
  for target in
    select table_name, column_name
    from information_schema.columns
    where table_schema = 'public'
      and table_name in (
        'contact_submissions', 'booking_requests', 'site_settings',
        'project_tech_stack', 'blog_post_tags', 'blog_tags',
        'service_deliverables', 'pricing_points'
      )
  loop
    foreach column_privilege in array array['SELECT', 'INSERT', 'UPDATE', 'REFERENCES']
    loop
      execute format(
        'revoke %s (%I) on table public.%I from public, anon, authenticated',
        column_privilege, target.column_name, target.table_name
      );
    end loop;
  end loop;
end
$$;

-- Visitor-controlled submission fields only. RLS checks constrain values;
-- the database supplies status/source defaults and keeps notes administrative.
grant insert (name, email, subject, message)
  on table public.contact_submissions to anon;
grant insert (name, email, whatsapp, service, budget, timeline, message)
  on table public.booking_requests to anon;
grant insert on table public.contact_submissions to service_role;
grant insert on table public.booking_requests to service_role;

-- Public renderers need these site settings and nested service/pricing fields.
-- Keep admin access intact while avoiding table-wide anon reads.
alter table public.site_settings enable row level security;
alter table public.project_tech_stack enable row level security;
alter table public.blog_tags enable row level security;
alter table public.blog_post_tags enable row level security;
alter table public.service_deliverables enable row level security;
alter table public.pricing_points enable row level security;

revoke select on table public.site_settings from public, anon, authenticated;
grant select (id, site_name, site_url, contact_email, contact_phone, location, github_url, linkedin_url, seo_title, seo_description)
  on table public.site_settings to anon;
grant select on table public.site_settings to service_role;

drop policy if exists "public can read site settings" on public.site_settings;
create policy "public can read site settings"
on public.site_settings
for select
to anon
using (true);

revoke select on table public.project_tech_stack from public, anon, authenticated;
grant select (project_id, label, sort_order) on table public.project_tech_stack to anon;
grant select on table public.project_tech_stack to service_role;

drop policy if exists "public can read published project tech stack" on public.project_tech_stack;
create policy "public can read published project tech stack"
on public.project_tech_stack
for select
to anon
using (
  exists (
    select 1 from public.projects
    where projects.id = project_tech_stack.project_id
      and projects.published = true
  )
);

revoke select on table public.blog_post_tags from public, anon, authenticated;
grant select (blog_post_id, blog_tag_id) on table public.blog_post_tags to anon;
grant select on table public.blog_post_tags to service_role;

drop policy if exists "public can read published blog post tags" on public.blog_post_tags;
create policy "public can read published blog post tags"
on public.blog_post_tags
for select
to anon
using (
  exists (
    select 1 from public.blog_posts
    where blog_posts.id = blog_post_tags.blog_post_id
      and blog_posts.published = true
  )
);

revoke select on table public.blog_tags from public, anon, authenticated;
grant select (id, label) on table public.blog_tags to anon;
grant select on table public.blog_tags to service_role;

drop policy if exists "public can read tags for published posts" on public.blog_tags;
create policy "public can read tags for published posts"
on public.blog_tags
for select
to anon
using (
  exists (
    select 1
    from public.blog_post_tags
    join public.blog_posts on blog_posts.id = blog_post_tags.blog_post_id
    where blog_post_tags.blog_tag_id = blog_tags.id
      and blog_posts.published = true
  )
);

revoke select on table public.service_deliverables from public, anon, authenticated;
grant select (service_id, label, sort_order) on table public.service_deliverables to anon;
grant select on table public.service_deliverables to service_role;

drop policy if exists "public can read visible service deliverables" on public.service_deliverables;
create policy "public can read visible service deliverables"
on public.service_deliverables
for select
to anon
using (
  exists (
    select 1 from public.services
    where services.id = service_deliverables.service_id
      and services.visible = true
  )
);

revoke select on table public.pricing_points from public, anon, authenticated;
grant select (pricing_tier_id, label, sort_order) on table public.pricing_points to anon;
grant select on table public.pricing_points to service_role;

drop policy if exists "public can read visible pricing points" on public.pricing_points;
create policy "public can read visible pricing points"
on public.pricing_points
for select
to anon
using (
  exists (
    select 1 from public.pricing_tiers
    where pricing_tiers.id = pricing_points.pricing_tier_id
      and pricing_tiers.visible = true
  )
);

drop policy if exists "public can submit contact inquiries" on public.contact_submissions;
create policy "public can submit contact inquiries"
on public.contact_submissions
for insert
to anon
with check (
  status = 'new'
  and source = 'portfolio'
  and notes is null
  and char_length(btrim(name)) between 1 and 120
  and char_length(email) between 5 and 254
  and email ~* '^[^[:space:]@]+@[^[:space:]@.]+(\.[^[:space:]@.]+)+$'
  and char_length(coalesce(subject, '')) <= 160
  and char_length(btrim(message)) between 1 and 5000
);

drop policy if exists "public can submit booking requests" on public.booking_requests;
create policy "public can submit booking requests"
on public.booking_requests
for insert
to anon
with check (
  status = 'new'
  and source = 'portfolio'
  and notes is null
  and char_length(btrim(name)) between 1 and 120
  and char_length(email) between 5 and 254
  and email ~* '^[^[:space:]@]+@[^[:space:]@.]+(\.[^[:space:]@.]+)+$'
  and char_length(coalesce(whatsapp, '')) <= 40
  and char_length(coalesce(service, '')) <= 120
  and char_length(coalesce(budget, '')) <= 120
  and char_length(coalesce(timeline, '')) <= 120
  and char_length(btrim(message)) between 1 and 5000
);
