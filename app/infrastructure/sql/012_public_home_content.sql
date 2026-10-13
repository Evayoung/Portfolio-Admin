-- Editable home-page copy, highlights, stats, and image URLs.
-- Image bytes remain in the public portfolio-media Storage bucket; the row
-- stores reusable public URLs so existing project/blog URL fields stay valid.

create table if not exists public.site_home_content (
  id text primary key default 'primary' check (id = 'primary'),
  hero_roles jsonb not null default '[]'::jsonb,
  hero_summary text not null default '',
  about_summary text not null default '',
  journey_paragraphs jsonb not null default '[]'::jsonb,
  about_stats jsonb not null default '[]'::jsonb,
  experience_items jsonb not null default '[]'::jsonb,
  technical_skills jsonb not null default '[]'::jsonb,
  cv_highlights jsonb not null default '[]'::jsonb,
  seo_keywords jsonb not null default '[]'::jsonb,
  profile_image_url text not null default '/assets/images/me-photo.jpg',
  hero_background_url text not null default '/assets/images/hero-bg4.jpg',
  booking_background_url text not null default '/assets/images/hero-bg2.jpg',
  cv_background_url text not null default '/assets/images/hero-bg4.jpg',
  updated_at timestamptz not null default timezone('utc', now())
);

alter table public.site_home_content enable row level security;
revoke all privileges on table public.site_home_content from public, anon, authenticated;
grant select (
  id, hero_roles, hero_summary, about_summary, journey_paragraphs, about_stats,
  experience_items, technical_skills, cv_highlights, seo_keywords, profile_image_url,
  hero_background_url, booking_background_url, cv_background_url, updated_at
) on table public.site_home_content to anon;
grant all privileges on table public.site_home_content to service_role;

drop policy if exists "public can read site home content" on public.site_home_content;
create policy "public can read site home content"
on public.site_home_content for select to anon
using (id = 'primary');

insert into public.site_home_content (
  id, hero_roles, hero_summary, about_summary, journey_paragraphs, about_stats,
  experience_items, technical_skills, cv_highlights, seo_keywords
)
values (
  'primary',
  '["Full-Stack Developer", "AI Systems Architect", "API & Backend Engineer", "Open-Source Builder"]'::jsonb,
  'I design and ship production-ready software at the intersection of Python, AI, and real-world operations. From multi-agent backend systems and offline-first accessibility tools to secure biometric platforms and data infrastructure, I build products that are meant to survive actual use.',
  'Full-Stack and AI Systems Architect with hands-on experience delivering reliable systems across web, mobile, desktop, and distributed environments.',
  '["I started as a statistics graduate who was curious about what software could make possible. That curiosity grew into a career built around designing systems that solve real problems for real people - from visually impaired students in Nigerian classrooms to operational teams that need better data, security, and automation.", "Today I work across the full stack: FastAPI backends, FastHTML and Reflex frontends, KivyMD mobile applications, AI-assisted workflows, and Linux-based device systems. I care most about architecture that holds up under real constraints - offline use, low-connectivity environments, operational complexity, and the need to keep software maintainable after launch."]'::jsonb,
  '[{"value":"10+","label":"Production Projects"},{"value":"5+","label":"Years Experience"},{"value":"3","label":"Active SaaS Products"},{"value":"2","label":"Institutional Systems"}]'::jsonb,
  '[{"year":"2024 - Present","title":"Full-Stack & AI Systems Architect","company":"Independent / Freelance","summary":"Designing and shipping production-grade systems across AI automation, security workflows, data infrastructure, and Python-native full-stack products."},{"year":"2023 - Present","title":"Python & Software Tutor","company":"SuperProf & Certmart","summary":"Teaching Python, software architecture, and AI literacy through practical delivery-focused learning plans."},{"year":"2024 - 2025","title":"Backend Lead","company":"University of Ilorin - Clinic & CBT Projects","summary":"Delivered institution-scale systems including a digital clinic platform and biometric exam access controls."}]'::jsonb,
  '[{"name":"Python / FastAPI","score":97,"badge":"Backend"},{"name":"FastHTML / Faststrap","score":95,"badge":"Full-Stack"},{"name":"AI & LLM Integration","score":92,"badge":"AI/ML"},{"name":"PostgreSQL / SQLite","score":90,"badge":"Database"},{"name":"Reflex (Full-Stack)","score":88,"badge":"Full-Stack"},{"name":"PySide6 / PyQt6","score":87,"badge":"Desktop"},{"name":"KivyMD (Mobile)","score":85,"badge":"Mobile"},{"name":"Linux / systemd","score":78,"badge":"DevOps"}]'::jsonb,
  '[{"title":"Specialisation","copy":"Python-first product delivery, AI orchestration systems, and cross-platform application architecture."},{"title":"Strengths","copy":"Production-grade FastAPI, LLM integration, offline-first thinking, and secure system design."},{"title":"Approach","copy":"Build what will hold up in the real world - clear architecture, practical tradeoffs, and dependable delivery."}]'::jsonb,
  '["Olorundare Micheal", "Full-Stack Developer", "AI Engineer", "FastAPI", "FastHTML", "Faststrap", "Python Developer", "Nigeria", "Ilorin", "Backend Developer", "AI Systems Architect", "KivyMD", "Reflex"]'::jsonb
)
on conflict (id) do nothing;
