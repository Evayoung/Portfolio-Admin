create extension if not exists pgcrypto;

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
  new.updated_at = timezone('utc', now());
  return new;
end;
$$;

create table if not exists public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  email text not null unique,
  full_name text not null,
  role text not null default 'admin' check (role in ('admin', 'editor')),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.site_settings (
  id uuid primary key default gen_random_uuid(),
  site_name text not null,
  site_url text not null,
  contact_email text,
  contact_phone text,
  location text,
  github_url text,
  linkedin_url text,
  seo_title text,
  seo_description text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.projects (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  category text not null,
  summary text not null,
  narrative text not null,
  image_url text,
  complexity smallint not null default 0 check (complexity between 0 and 100),
  satisfaction smallint not null default 0 check (satisfaction between 0 and 100),
  featured boolean not null default false,
  published boolean not null default false,
  published_at timestamptz,
  sort_order integer not null default 100,
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.project_tech_stack (
  id uuid primary key default gen_random_uuid(),
  project_id uuid not null references public.projects(id) on delete cascade,
  label text not null,
  sort_order integer not null default 100
);

create table if not exists public.blog_posts (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  category text not null,
  summary text not null,
  content_html text not null,
  image_url text,
  read_minutes integer not null default 5,
  published boolean not null default false,
  published_at timestamptz,
  created_by uuid references public.profiles(id),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.blog_tags (
  id uuid primary key default gen_random_uuid(),
  label text not null unique,
  created_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.blog_post_tags (
  blog_post_id uuid not null references public.blog_posts(id) on delete cascade,
  blog_tag_id uuid not null references public.blog_tags(id) on delete cascade,
  primary key (blog_post_id, blog_tag_id)
);

create table if not exists public.testimonials (
  id uuid primary key default gen_random_uuid(),
  author text not null,
  role text,
  company text,
  quote text not null,
  visible boolean not null default true,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.services (
  id uuid primary key default gen_random_uuid(),
  slug text not null unique,
  title text not null,
  summary text not null,
  lead text not null,
  timeline text,
  price text,
  icon text,
  visible boolean not null default true,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.service_deliverables (
  id uuid primary key default gen_random_uuid(),
  service_id uuid not null references public.services(id) on delete cascade,
  label text not null,
  sort_order integer not null default 100
);

create table if not exists public.pricing_tiers (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  price text not null,
  highlight text not null,
  visible boolean not null default true,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.pricing_points (
  id uuid primary key default gen_random_uuid(),
  pricing_tier_id uuid not null references public.pricing_tiers(id) on delete cascade,
  label text not null,
  sort_order integer not null default 100
);

create table if not exists public.cv_meta (
  id uuid primary key default gen_random_uuid(),
  full_name text not null,
  role text not null,
  email text,
  phone text,
  whatsapp text,
  location text,
  github_url text,
  linkedin_url text,
  summary text not null,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_work_history (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  organisation text not null,
  period text not null,
  location text,
  bullets jsonb not null default '[]'::jsonb,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_education (
  id uuid primary key default gen_random_uuid(),
  degree text not null,
  institution text not null,
  period text not null,
  note text,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_certifications (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  issuer text not null,
  year text not null,
  credential_url text,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_tool_categories (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  tools jsonb not null default '[]'::jsonb,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_languages (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  proficiency_label text not null,
  proficiency_score smallint not null check (proficiency_score between 0 and 100),
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_core_skills (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.cv_competencies (
  id uuid primary key default gen_random_uuid(),
  label text not null,
  sort_order integer not null default 100,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.contact_submissions (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  subject text,
  message text not null,
  status text not null default 'new' check (status in ('new', 'in_progress', 'closed', 'spam')),
  source text not null default 'portfolio',
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create table if not exists public.booking_requests (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  email text not null,
  whatsapp text,
  service text,
  budget text,
  timeline text,
  message text not null,
  status text not null default 'new' check (status in ('new', 'reviewing', 'scheduled', 'closed', 'spam')),
  source text not null default 'portfolio',
  notes text,
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now())
);

create index if not exists idx_projects_published_sort on public.projects (sort_order, published_at desc) where published = true;
create index if not exists idx_projects_category on public.projects (category);
create index if not exists idx_projects_featured on public.projects (featured) where featured = true;
create index if not exists idx_blog_posts_published_sort on public.blog_posts (published_at desc) where published = true;
create index if not exists idx_contact_submissions_status on public.contact_submissions (status, created_at desc);
create index if not exists idx_booking_requests_status on public.booking_requests (status, created_at desc);

create trigger set_profiles_updated_at
before update on public.profiles
for each row execute function public.set_updated_at();

create trigger set_site_settings_updated_at
before update on public.site_settings
for each row execute function public.set_updated_at();

create trigger set_projects_updated_at
before update on public.projects
for each row execute function public.set_updated_at();

create trigger set_blog_posts_updated_at
before update on public.blog_posts
for each row execute function public.set_updated_at();

create trigger set_testimonials_updated_at
before update on public.testimonials
for each row execute function public.set_updated_at();

create trigger set_services_updated_at
before update on public.services
for each row execute function public.set_updated_at();

create trigger set_pricing_tiers_updated_at
before update on public.pricing_tiers
for each row execute function public.set_updated_at();

create trigger set_cv_meta_updated_at
before update on public.cv_meta
for each row execute function public.set_updated_at();

create trigger set_cv_work_history_updated_at
before update on public.cv_work_history
for each row execute function public.set_updated_at();

create trigger set_cv_education_updated_at
before update on public.cv_education
for each row execute function public.set_updated_at();

create trigger set_cv_certifications_updated_at
before update on public.cv_certifications
for each row execute function public.set_updated_at();

create trigger set_cv_tool_categories_updated_at
before update on public.cv_tool_categories
for each row execute function public.set_updated_at();

create trigger set_cv_languages_updated_at
before update on public.cv_languages
for each row execute function public.set_updated_at();

create trigger set_cv_core_skills_updated_at
before update on public.cv_core_skills
for each row execute function public.set_updated_at();

create trigger set_cv_competencies_updated_at
before update on public.cv_competencies
for each row execute function public.set_updated_at();

create trigger set_contact_submissions_updated_at
before update on public.contact_submissions
for each row execute function public.set_updated_at();

create trigger set_booking_requests_updated_at
before update on public.booking_requests
for each row execute function public.set_updated_at();

alter table public.profiles enable row level security;
alter table public.site_settings enable row level security;
alter table public.projects enable row level security;
alter table public.project_tech_stack enable row level security;
alter table public.blog_posts enable row level security;
alter table public.blog_tags enable row level security;
alter table public.blog_post_tags enable row level security;
alter table public.testimonials enable row level security;
alter table public.services enable row level security;
alter table public.service_deliverables enable row level security;
alter table public.pricing_tiers enable row level security;
alter table public.pricing_points enable row level security;
alter table public.cv_meta enable row level security;
alter table public.cv_work_history enable row level security;
alter table public.cv_education enable row level security;
alter table public.cv_certifications enable row level security;
alter table public.cv_tool_categories enable row level security;
alter table public.cv_languages enable row level security;
alter table public.cv_core_skills enable row level security;
alter table public.cv_competencies enable row level security;
alter table public.contact_submissions enable row level security;
alter table public.booking_requests enable row level security;

create or replace function public.is_admin()
returns boolean
language sql
stable
as $$
  select exists (
    select 1
    from public.profiles
    where id = auth.uid()
      and role = 'admin'
  );
$$;

create policy "public can read published projects"
on public.projects
for select
using (published = true);

create policy "public can read published blog posts"
on public.blog_posts
for select
using (published = true);

create policy "public can read visible testimonials"
on public.testimonials
for select
using (visible = true);

create policy "public can read visible services"
on public.services
for select
using (visible = true);

create policy "public can read visible pricing tiers"
on public.pricing_tiers
for select
using (visible = true);

create policy "public can read cv meta"
on public.cv_meta
for select
using (true);

create policy "public can read cv work history"
on public.cv_work_history
for select
using (true);

create policy "public can read cv education"
on public.cv_education
for select
using (true);

create policy "public can read cv certifications"
on public.cv_certifications
for select
using (true);

create policy "public can read cv tool categories"
on public.cv_tool_categories
for select
using (true);

create policy "public can read cv languages"
on public.cv_languages
for select
using (true);

create policy "public can read cv core skills"
on public.cv_core_skills
for select
using (true);

create policy "public can read cv competencies"
on public.cv_competencies
for select
using (true);

create policy "admins manage profiles"
on public.profiles
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage site settings"
on public.site_settings
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage projects"
on public.projects
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage project tech stack"
on public.project_tech_stack
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage blog posts"
on public.blog_posts
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage blog tags"
on public.blog_tags
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage blog post tags"
on public.blog_post_tags
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage testimonials"
on public.testimonials
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage services"
on public.services
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage service deliverables"
on public.service_deliverables
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage pricing tiers"
on public.pricing_tiers
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage pricing points"
on public.pricing_points
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv meta"
on public.cv_meta
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv work history"
on public.cv_work_history
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv education"
on public.cv_education
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv certifications"
on public.cv_certifications
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv tool categories"
on public.cv_tool_categories
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv languages"
on public.cv_languages
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv core skills"
on public.cv_core_skills
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage cv competencies"
on public.cv_competencies
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage contact submissions"
on public.contact_submissions
for all
using (public.is_admin())
with check (public.is_admin());

create policy "admins manage booking requests"
on public.booking_requests
for all
using (public.is_admin())
with check (public.is_admin());
