-- Initial Schema Creation for LinguaFormula
-- Run this script FIRST to create the base tables
-- Then run schema_migration.sql to add enhancements

-- ============================================================================
-- BASE TABLES
-- ============================================================================

-- Formula table - Core formula data
CREATE TABLE IF NOT EXISTS formula (
    id SERIAL PRIMARY KEY,
    formula_name VARCHAR(100) NOT NULL,
    latex TEXT NOT NULL,
    display_order INTEGER,
    formula_description TEXT,
    english_verbalization TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Application table - Problem/application data
CREATE TABLE IF NOT EXISTS application (
    id SERIAL PRIMARY KEY,
    title VARCHAR(200) NOT NULL,
    problem_text TEXT NOT NULL,
    subject_area VARCHAR(50),  -- e.g., 'physics', 'statistics'
    image_filename VARCHAR(255),  -- Store filename/path of uploaded image
    image_data BYTEA,  -- Store binary image data
    image_text TEXT,  -- Store extracted text from image (OCR/AI parsing)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Association table for many-to-many relationship between Applications and Formulas
CREATE TABLE IF NOT EXISTS application_formula (
    application_id INTEGER NOT NULL REFERENCES application(id) ON DELETE CASCADE,
    formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    relevance_score FLOAT,  -- Optional: AI-generated relevance score
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (application_id, formula_id)
);

-- ============================================================================
-- INDEXES for better query performance
-- ============================================================================

CREATE INDEX IF NOT EXISTS idx_formula_display_order ON formula(display_order);
CREATE INDEX IF NOT EXISTS idx_formula_name ON formula(formula_name);
CREATE INDEX IF NOT EXISTS idx_application_subject_area ON application(subject_area);
CREATE INDEX IF NOT EXISTS idx_application_formula_app_id ON application_formula(application_id);
CREATE INDEX IF NOT EXISTS idx_application_formula_formula_id ON application_formula(formula_id);

-- ============================================================================
-- COMMENTS
-- ============================================================================

COMMENT ON TABLE formula IS 'Core table storing mathematical formulas with LaTeX and English descriptions';
COMMENT ON TABLE application IS 'Stores problem/application data that can be matched to formulas';
COMMENT ON TABLE application_formula IS 'Many-to-many relationship between applications and formulas';
