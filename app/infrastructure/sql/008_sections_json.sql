-- Add sections_json column to client_deals for dynamic document sections

alter table public.client_deals
add column if not exists sections_json text not null default '';
