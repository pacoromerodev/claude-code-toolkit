-- NOT NULL with no default on an existing table: fails on any existing row.
ALTER TABLE customers ADD COLUMN tax_region VARCHAR(8) NOT NULL;
