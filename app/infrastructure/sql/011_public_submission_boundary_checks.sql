-- Read-only checks for 011_public_submission_boundary.sql.
-- Run before and after the migration in the staging Supabase SQL editor.
-- These queries inspect schema, grants, and policies only; they do not read
-- submission or portfolio content.

-- 1. Confirm all tables and columns referenced by migration 011 exist.
select table_name, column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public'
  and (
    (table_name = 'contact_submissions' and column_name in
      ('name', 'email', 'subject', 'message', 'status', 'source', 'notes'))
    or (table_name = 'booking_requests' and column_name in
      ('name', 'email', 'whatsapp', 'service', 'budget', 'timeline', 'message', 'status', 'source', 'notes'))
    or (table_name = 'site_settings' and column_name in
      ('id', 'site_name', 'site_url', 'contact_email', 'contact_phone', 'location', 'github_url', 'linkedin_url', 'seo_title', 'seo_description'))
    or (table_name = 'project_tech_stack' and column_name in ('project_id', 'label', 'sort_order'))
    or (table_name = 'blog_post_tags' and column_name in ('blog_post_id', 'blog_tag_id'))
    or (table_name = 'blog_tags' and column_name in ('id', 'label'))
    or (table_name = 'service_deliverables' and column_name in ('service_id', 'label', 'sort_order'))
    or (table_name = 'pricing_points' and column_name in ('pricing_tier_id', 'label', 'sort_order'))
  )
order by table_name, ordinal_position;

-- 2. Check RLS is enabled on the affected tables.
select c.relname as table_name, c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public'
  and c.relname in (
    'contact_submissions', 'booking_requests', 'site_settings',
    'project_tech_stack', 'blog_post_tags', 'blog_tags',
    'service_deliverables', 'pricing_points'
  )
order by c.relname;

-- 3. Inspect relevant policies. Before migration, the two public INSERT
-- policies and six public site/child read policies should be absent.
select tablename, policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public'
  and tablename in (
    'contact_submissions', 'booking_requests', 'site_settings',
    'project_tech_stack', 'blog_post_tags', 'blog_tags',
    'service_deliverables', 'pricing_points'
  )
order by tablename, policyname;

-- 4. Inspect effective anon column privileges. Before migration, broad grants
-- may make these true. Afterward, submission INSERT is allowed only for
-- visitor fields; submission SELECT and protected-field INSERT are false.
-- Public content SELECT is true only for fields listed in migration 011;
-- public content INSERT is false.
select
  table_name,
  column_name,
  has_column_privilege('anon', format('public.%I', table_name), column_name, 'INSERT') as anon_can_insert,
  has_column_privilege('anon', format('public.%I', table_name), column_name, 'SELECT') as anon_can_select
from (values
  ('contact_submissions', 'name'),
  ('contact_submissions', 'email'),
  ('contact_submissions', 'subject'),
  ('contact_submissions', 'message'),
  ('contact_submissions', 'status'),
  ('contact_submissions', 'source'),
  ('contact_submissions', 'notes'),
  ('booking_requests', 'name'),
  ('booking_requests', 'email'),
  ('booking_requests', 'whatsapp'),
  ('booking_requests', 'service'),
  ('booking_requests', 'budget'),
  ('booking_requests', 'timeline'),
  ('booking_requests', 'message'),
  ('booking_requests', 'status'),
  ('booking_requests', 'source'),
  ('booking_requests', 'notes'),
  ('site_settings', 'site_name'),
  ('site_settings', 'seo_title'),
  ('project_tech_stack', 'project_id'),
  ('project_tech_stack', 'label'),
  ('blog_post_tags', 'blog_post_id'),
  ('blog_post_tags', 'blog_tag_id'),
  ('blog_tags', 'label'),
  ('service_deliverables', 'service_id'),
  ('service_deliverables', 'label'),
  ('pricing_points', 'pricing_tier_id'),
  ('pricing_points', 'label')
) as expected(table_name, column_name)
order by table_name, column_name;

-- 5. Confirm service_role retained full table access for Neo Admin.
select
  table_name,
  has_table_privilege('service_role', format('public.%I', table_name), 'SELECT') as service_role_can_select,
  has_table_privilege('service_role', format('public.%I', table_name), 'INSERT') as service_role_can_insert,
  has_table_privilege('service_role', format('public.%I', table_name), 'UPDATE') as service_role_can_update,
  has_table_privilege('service_role', format('public.%I', table_name), 'DELETE') as service_role_can_delete
from (values
  ('contact_submissions'), ('booking_requests'), ('site_settings'),
  ('project_tech_stack'), ('blog_post_tags'), ('blog_tags'),
  ('service_deliverables'), ('pricing_points')
) as expected(table_name)
order by table_name;
