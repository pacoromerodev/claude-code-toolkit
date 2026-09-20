-- A new table: nothing is reading it yet, so nothing can break.
CREATE TABLE shipment (
    id          BIGINT PRIMARY KEY,
    order_id    BIGINT NOT NULL,
    carrier     VARCHAR(32) NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
