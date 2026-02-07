-- Migration: add payment table
CREATE TABLE IF NOT EXISTS payment (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bill_id INTEGER REFERENCES bill(id) ON DELETE SET NULL,
    unit_id INTEGER REFERENCES unit(id) ON DELETE SET NULL,
    amount NUMERIC(18,4) NOT NULL,
    method VARCHAR(64),
    reference VARCHAR(128),
    received_at DATETIME NOT NULL DEFAULT (CURRENT_TIMESTAMP)
);

CREATE INDEX IF NOT EXISTS ix_payment_bill_id ON payment(bill_id);
CREATE INDEX IF NOT EXISTS ix_payment_unit_id ON payment(unit_id);
