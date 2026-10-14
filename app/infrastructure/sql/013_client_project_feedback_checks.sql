-- Read-only checks for 013_client_project_feedback.sql.

select column_name, data_type, is_nullable
from information_schema.columns
where table_schema = 'public' and table_name = 'client_project_feedback'
order by ordinal_position;

select c.relname as table_name, c.relrowsecurity as rls_enabled
from pg_class c
join pg_namespace n on n.oid = c.relnamespace
where n.nspname = 'public' and c.relname = 'client_project_feedback';

select policyname, roles, cmd, qual, with_check
from pg_policies
where schemaname = 'public' and tablename = 'client_project_feedback';

select
  has_table_privilege('anon', 'public.client_project_feedback', 'SELECT') as anon_can_select,
  has_table_privilege('anon', 'public.client_project_feedback', 'INSERT') as anon_can_insert,
  has_table_privilege('anon', 'public.client_project_feedback', 'UPDATE') as anon_can_update,
  has_table_privilege('service_role', 'public.client_project_feedback', 'SELECT') as service_role_can_select,
  has_table_privilege('service_role', 'public.client_project_feedback', 'INSERT') as service_role_can_insert,
  has_table_privilege('service_role', 'public.client_project_feedback', 'UPDATE') as service_role_can_update;
