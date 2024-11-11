-- Create tables in dependency order

-- 1. Create Customer table with ON CONFLICT support
CREATE TABLE IF NOT EXISTS customer (
    customer_id VARCHAR PRIMARY KEY,
    customer_name VARCHAR NOT NULL,
    account_number VARCHAR NOT NULL
);

-- 2. Create Facility table with ON CONFLICT support 
CREATE TABLE IF NOT EXISTS facility (
    internal_facility_id VARCHAR PRIMARY KEY,     -- Generated unique ID
    facility_id VARCHAR NOT NULL,
    customer_id VARCHAR NOT NULL,
    facility_name VARCHAR NOT NULL,
    facility_type VARCHAR NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    UNIQUE (customer_id, facility_id)    -- Added for UPSERT support
);

-- 3. Create Invoice table with ON CONFLICT support
CREATE TABLE IF NOT EXISTS invoice (
    invoice_id VARCHAR PRIMARY KEY,
    invoice_number VARCHAR NOT NULL,
    customer_id VARCHAR NOT NULL,
    internal_facility_id VARCHAR NOT NULL,
    invoice_date DATE NOT NULL,
    invoice_amount DECIMAL(18, 2) NOT NULL,
    additional_charges DECIMAL(18, 2),
    discounts_applied DECIMAL(18, 2),
    amount_paid DECIMAL(18, 2) NOT NULL DEFAULT 0,
    facility_type VARCHAR NOT NULL,
    service_type VARCHAR,
    usage_amount DECIMAL(18, 6),
    usage_unit VARCHAR,
    rate_type VARCHAR,
    co2_supplementation DECIMAL(18, 2),
    status VARCHAR NOT NULL,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id),
    FOREIGN KEY (internal_facility_id) REFERENCES facility(internal_facility_id),
    UNIQUE (customer_id, invoice_number)    -- Added for UPSERT support
);

-- 4. Create CO2 Supplementation Rate table with ON CONFLICT support
CREATE TABLE IF NOT EXISTS co2_supplementation_rate (
    rate_id VARCHAR PRIMARY KEY,
    internal_facility_id VARCHAR NOT NULL,
    effective_date DATE NOT NULL,
    rate DECIMAL(18, 6) NOT NULL,
    FOREIGN KEY (internal_facility_id) REFERENCES facility(internal_facility_id),
    UNIQUE (internal_facility_id, effective_date)    -- Added for UPSERT support
);

-- 5. Create Payment table with ON CONFLICT support
CREATE TABLE IF NOT EXISTS payment (
    payment_id VARCHAR PRIMARY KEY,
    customer_id VARCHAR NOT NULL,
    payment_date DATE NOT NULL,
    bank_account_number VARCHAR NOT NULL,
    total_payment_paid DECIMAL(18, 2) NOT NULL,
    payment_reference VARCHAR NOT NULL UNIQUE,
    payment_method VARCHAR NOT NULL,
    total_invoice_amount DECIMAL(18, 2) NOT NULL,
    total_additional_charges DECIMAL(18, 2),
    total_discounts_applied DECIMAL(18, 2),
    total_invoices INTEGER NOT NULL,
    remittance_notes TEXT,
    FOREIGN KEY (customer_id) REFERENCES customer(customer_id)
);

-- 6. Create Payment Allocation table with ON CONFLICT support
CREATE TABLE IF NOT EXISTS payment_allocation (
    allocation_id VARCHAR PRIMARY KEY,
    payment_id VARCHAR NOT NULL,
    invoice_id VARCHAR NOT NULL,
    amount_applied DECIMAL(18, 2) NOT NULL,
    invoice_amount DECIMAL(18, 2) NOT NULL,
    discounts_applied DECIMAL(18, 2),
    additional_charges DECIMAL(18, 2),
    FOREIGN KEY (payment_id) REFERENCES payment(payment_id),
    FOREIGN KEY (invoice_id) REFERENCES invoice(invoice_id),
    UNIQUE (payment_id, invoice_id)
);
