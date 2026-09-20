-- Nullable and defaulted: the running version ignores it, new rows get a value.
ALTER TABLE orders ADD COLUMN channel VARCHAR(16) DEFAULT 'WEB';
