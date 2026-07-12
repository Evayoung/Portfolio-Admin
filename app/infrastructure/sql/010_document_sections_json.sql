-- Add sections_json column to client_documents so each document carries its own sections.
-- This ensures generated quotes/invoices inherit sections from the accepted proposal.

alter table public.client_documents
add column if not exists sections_json text not null default '';
