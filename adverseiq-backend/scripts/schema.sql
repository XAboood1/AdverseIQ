-- -------------------------------------------------------
-- AdverseIQ Schema
-- Run this once in the Supabase SQL Editor to create tables.
-- Re-run any time you need a clean slate (drops existing tables).
-- -------------------------------------------------------

DROP TABLE IF EXISTS analyses     CASCADE;
DROP TABLE IF EXISTS interactions CASCADE;
DROP TABLE IF EXISTS herbs        CASCADE;
DROP TABLE IF EXISTS drugs        CASCADE;

CREATE TABLE drugs (
    id           SERIAL PRIMARY KEY,
    brand_name   VARCHAR(255) NOT NULL UNIQUE,
    generic_name VARCHAR(255) NOT NULL
);

CREATE TABLE interactions (
    id          SERIAL PRIMARY KEY,
    drug_a      VARCHAR(255) NOT NULL,
    drug_b      VARCHAR(255) NOT NULL,
    severity    VARCHAR(50),
    mechanism   TEXT,
    description TEXT,
    source      VARCHAR(50) DEFAULT 'database',
    UNIQUE (drug_a, drug_b)
);

CREATE TABLE herbs (
    id               SERIAL PRIMARY KEY,
    name             VARCHAR(255) NOT NULL UNIQUE,
    aliases          JSONB DEFAULT '[]',
    mechanisms       JSONB DEFAULT '[]',
    affected_drugs   JSONB DEFAULT '[]',
    interaction_note TEXT
);

CREATE TABLE analyses (
    id          VARCHAR(255) PRIMARY KEY,
    created_at  TIMESTAMP DEFAULT NOW(),
    input_json  TEXT,
    result_json TEXT
);

CREATE INDEX idx_interactions_drug_a ON interactions (LOWER(drug_a));
CREATE INDEX idx_interactions_drug_b ON interactions (LOWER(drug_b));
CREATE INDEX idx_drugs_brand         ON drugs (LOWER(brand_name));
CREATE INDEX idx_drugs_generic       ON drugs (LOWER(generic_name));
