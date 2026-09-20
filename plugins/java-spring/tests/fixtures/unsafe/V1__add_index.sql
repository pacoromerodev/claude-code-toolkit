-- Locks writes on a large table for the whole build.
CREATE INDEX idx_orders_customer ON orders (customer_id);
