-- Add 'rejected' to the allowed status values for client_documents.
-- The current check constraint only allows: draft, sent, accepted, paid, expired.
-- Rejection is a valid document state tracked by save_document_response().

ALTER TABLE public.client_documents
    DROP CONSTRAINT IF EXISTS client_documents_status_check;

ALTER TABLE public.client_documents
    ADD CONSTRAINT client_documents_status_check
    CHECK (status IN ('draft', 'sent', 'accepted', 'rejected', 'paid', 'expired'));
