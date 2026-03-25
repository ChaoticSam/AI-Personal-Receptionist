-- Run once on Postgres (e.g. Supabase SQL editor) if the table does not exist.

CREATE TABLE IF NOT EXISTS agent_order_drafts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    call_id UUID NOT NULL REFERENCES calls(id) ON DELETE CASCADE,
    business_id UUID NOT NULL REFERENCES businesses(id),
    customer_id UUID NOT NULL REFERENCES customers(id),
    product_id UUID REFERENCES products(id),
    quantity INTEGER NOT NULL DEFAULT 1,
    order_notes TEXT,
    custom_fields JSONB DEFAULT '{}'::jsonb,
    status VARCHAR NOT NULL DEFAULT 'collecting',
    placed_order_id UUID REFERENCES orders(id),
    last_idempotency_key VARCHAR,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_agent_order_drafts_call_id UNIQUE (call_id)
);

CREATE INDEX IF NOT EXISTS ix_agent_order_drafts_business_id ON agent_order_drafts (business_id);
