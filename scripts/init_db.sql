-- SyntaxLens Database Initialization Script
-- Enforces separation of identity vs research schema and immutable research records

CREATE SCHEMA IF NOT EXISTS identity;
CREATE SCHEMA IF NOT EXISTS research;

-- Research Integrity: Generic Immutability Trigger Function
CREATE OR REPLACE FUNCTION prevent_row_mutation_or_deletion()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'RESEARCH INTEGRITY VIOLATION: Records in table %.% are strictly append-only and cannot be updated or deleted.', TG_TABLE_SCHEMA, TG_TABLE_NAME;
END;
$$ LANGUAGE plpgsql;
