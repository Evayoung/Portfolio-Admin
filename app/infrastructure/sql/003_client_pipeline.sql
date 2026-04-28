create table if not exists public.client_deals (
    id uuid primary key default gen_random_uuid(),
    client_name text not null,
    client_email text not null default '',
    client_phone text not null default '',
    company text not null default '',
    project_title text not null,
    service_type text not null default 'custom-build',
    stage text not null default 'lead'
        check (stage in ('lead', 'proposal', 'quoted', 'invoiced', 'paid', 'delivered')),
    summary text not null default '',
    background_text text not null default '',
    scope_notes text not null default '',
    option_notes_text text not null default '',
    tech_stack jsonb not null default '[]'::jsonb,
    timeline_text text not null default '',
    payment_terms text not null default '',
    exclusions_text text not null default '',
    closing_note text not null default '',
    amount_ngn integer not null default 0,
    deposit_percent integer not null default 50,
    source_kind text not null default 'manual',
    source_entry_id text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists public.client_documents (
    id uuid primary key default gen_random_uuid(),
    deal_id uuid not null references public.client_deals(id) on delete cascade,
    kind text not null
        check (kind in ('proposal', 'quote', 'invoice')),
    status text not null default 'draft'
        check (status in ('draft', 'sent', 'accepted', 'paid', 'expired')),
    document_number text not null,
    title text not null,
    summary text not null default '',
    timeline_text text not null default '',
    payment_terms text not null default '',
    line_items jsonb not null default '[]'::jsonb,
    subtotal integer not null default 0,
    tax_amount integer not null default 0,
    total_amount integer not null default 0,
    valid_until date,
    due_date date,
    public_token text not null default '',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (deal_id, kind),
    unique (document_number)
);
