create table if not exists public.payment_accounts (
    id uuid primary key default gen_random_uuid(),
    label text not null,
    bank_name text not null,
    account_name text not null,
    account_number text not null,
    note text not null default '',
    is_default boolean not null default false,
    created_at timestamptz not null default now()
);

create table if not exists public.client_document_responses (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references public.client_documents(id) on delete cascade,
    action text not null
        check (action in ('accepted', 'rejected', 'commented', 'payment_submitted')),
    responder_name text not null default '',
    responder_email text not null default '',
    comment text not null default '',
    created_at timestamptz not null default now()
);

alter table public.client_documents
add column if not exists payment_account_id uuid references public.payment_accounts(id);
