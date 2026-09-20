-- Built without blocking writes. Runs outside a transaction.
CREATE INDEX CONCURRENTLY idx_shipment_order ON shipment (order_id);
