-- Read-only checks for 012_public_home_content.sql.

select table_name, column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public'
  and table_name = 'site_home_content'
order by ordinal_position;

select c.relname as table_name, c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname = 'site_home_content';

select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'site_home_content';

select
  has_column_privilege('anon', 'public.site_home_content', 'hero_summary', 'SELECT') as anon_can_read_home_copy,
  has_column_privilege('anon', 'public.site_home_content', 'profile_image_url', 'SELECT') as anon_can_read_image_urls,
  has_column_privilege('anon', 'public.site_home_content', 'hero_summary', 'UPDATE') as anon_can_update_home_copy,
  has_table_privilege('service_role', 'public.site_home_content', 'UPDATE') as service_role_can_update_home_copy;

select count(*) as primary_content_rows
from public.site_home_content
where id = 'primary';
