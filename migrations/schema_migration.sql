-- Schema Migration Script for Enhanced Formula System
-- Run this script to upgrade from basic schema to enhanced schema

-- ============================================================================
-- PHASE 1: Add new columns to existing tables (non-breaking changes)
-- ============================================================================

-- Enhance Formula table with new metadata columns
ALTER TABLE formula ADD COLUMN IF NOT EXISTS category VARCHAR(50);
ALTER TABLE formula ADD COLUMN IF NOT EXISTS difficulty_level VARCHAR(20);
ALTER TABLE formula ADD COLUMN IF NOT EXISTS assumptions TEXT;
ALTER TABLE formula ADD COLUMN IF NOT EXISTS formula_expression TEXT;
ALTER TABLE formula ADD COLUMN IF NOT EXISTS output_target VARCHAR(100);

-- Enhance application_formula table with new relationship data
ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS variable_mapping JSONB;
ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS solution_steps TEXT;
ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS confidence_score FLOAT;
ALTER TABLE application_formula ADD COLUMN IF NOT EXISTS missing_variables TEXT[];

-- ============================================================================
-- PHASE 2: Create new tables for enhanced functionality
-- ============================================================================

-- Formula Variables Table - Track input/output parameters
CREATE TABLE IF NOT EXISTS formula_variables (
    id SERIAL PRIMARY KEY,
    formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    variable_name VARCHAR(50) NOT NULL,
    variable_type VARCHAR(20) NOT NULL CHECK (variable_type IN ('input', 'output')),
    description TEXT,
    units VARCHAR(50),
    is_required BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Formula Relationships Table - Helper formula dependencies
CREATE TABLE IF NOT EXISTS formula_relationships (
    id SERIAL PRIMARY KEY,
    main_formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    helper_formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    relationship_type VARCHAR(50) NOT NULL CHECK (relationship_type IN ('prerequisite', 'helper', 'alternative')),
    usage_context TEXT,
    sequence_order INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(main_formula_id, helper_formula_id, relationship_type)
);

-- Formula Keywords Table - Search terms and tags
CREATE TABLE IF NOT EXISTS formula_keywords (
    id SERIAL PRIMARY KEY,
    formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    keyword VARCHAR(100) NOT NULL,
    keyword_type VARCHAR(30) NOT NULL CHECK (keyword_type IN ('subject', 'concept', 'method', 'application')),
    weight FLOAT DEFAULT 1.0 CHECK (weight >= 0.1 AND weight <= 1.0),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Formula Examples Table - Built-in example problems
CREATE TABLE IF NOT EXISTS formula_examples (
    id SERIAL PRIMARY KEY,
    formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    example_title VARCHAR(200),
    example_problem TEXT NOT NULL,
    given_values JSONB,
    solution_steps TEXT,
    final_answer TEXT,
    difficulty_level VARCHAR(20) CHECK (difficulty_level IN ('beginner', 'intermediate', 'advanced')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Formula Prerequisites Table - Required knowledge
CREATE TABLE IF NOT EXISTS formula_prerequisites (
    id SERIAL PRIMARY KEY,
    formula_id INTEGER NOT NULL REFERENCES formula(id) ON DELETE CASCADE,
    prerequisite_concept VARCHAR(200) NOT NULL,
    importance_level VARCHAR(20) DEFAULT 'medium' CHECK (importance_level IN ('low', 'medium', 'high', 'critical')),
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PHASE 3: Create indexes for performance
-- ============================================================================

-- Indexes for formula_variables
CREATE INDEX IF NOT EXISTS idx_formula_variables_formula_id ON formula_variables(formula_id);
CREATE INDEX IF NOT EXISTS idx_formula_variables_type ON formula_variables(variable_type);

-- Indexes for formula_relationships
CREATE INDEX IF NOT EXISTS idx_formula_relationships_main ON formula_relationships(main_formula_id);
CREATE INDEX IF NOT EXISTS idx_formula_relationships_helper ON formula_relationships(helper_formula_id);
CREATE INDEX IF NOT EXISTS idx_formula_relationships_type ON formula_relationships(relationship_type);

-- Indexes for formula_keywords
CREATE INDEX IF NOT EXISTS idx_formula_keywords_formula_id ON formula_keywords(formula_id);
CREATE INDEX IF NOT EXISTS idx_formula_keywords_keyword ON formula_keywords(keyword);
CREATE INDEX IF NOT EXISTS idx_formula_keywords_type ON formula_keywords(keyword_type);

-- Indexes for formula_examples
CREATE INDEX IF NOT EXISTS idx_formula_examples_formula_id ON formula_examples(formula_id);
CREATE INDEX IF NOT EXISTS idx_formula_examples_difficulty ON formula_examples(difficulty_level);

-- Indexes for formula_prerequisites
CREATE INDEX IF NOT EXISTS idx_formula_prerequisites_formula_id ON formula_prerequisites(formula_id);

-- Indexes for enhanced formula table
CREATE INDEX IF NOT EXISTS idx_formula_category ON formula(category);
CREATE INDEX IF NOT EXISTS idx_formula_difficulty ON formula(difficulty_level);

-- ============================================================================
-- PHASE 4: Insert sample data for Bayes Theorem (demonstration)
-- ============================================================================

-- Sample enhanced data for Bayes Theorem (assuming it exists as formula id 1)
-- Note: This is conditional - only insert if Bayes Theorem doesn't already have enhanced data

DO $$
DECLARE
    bayes_formula_id INTEGER;
BEGIN
    -- Find Bayes Theorem formula (adjust the search criteria as needed)
    SELECT id INTO bayes_formula_id 
    FROM formula 
    WHERE LOWER(formula_name) LIKE '%bayes%' 
    LIMIT 1;
    
    IF bayes_formula_id IS NOT NULL THEN
        -- Update formula with enhanced metadata
        UPDATE formula 
        SET category = 'Probability',
            difficulty_level = 'intermediate',
            assumptions = 'Events A and B are defined on the same sample space',
            output_target = 'P(B|A)'
        WHERE id = bayes_formula_id;
        
        -- Insert variables
        INSERT INTO formula_variables (formula_id, variable_name, variable_type, description) VALUES
        (bayes_formula_id, 'P(A|B)', 'input', 'Probability of A given B'),
        (bayes_formula_id, 'P(B)', 'input', 'Prior probability of B'),
        (bayes_formula_id, 'P(A)', 'input', 'Prior probability of A'),
        (bayes_formula_id, 'P(B|A)', 'output', 'Posterior probability of B given A')
        ON CONFLICT DO NOTHING;
        
        -- Insert keywords
        INSERT INTO formula_keywords (formula_id, keyword, keyword_type, weight) VALUES
        (bayes_formula_id, 'bayes', 'method', 1.0),
        (bayes_formula_id, 'conditional', 'concept', 0.9),
        (bayes_formula_id, 'posterior', 'concept', 0.8),
        (bayes_formula_id, 'inverse probability', 'concept', 0.7)
        ON CONFLICT DO NOTHING;
        
        -- Insert example
        INSERT INTO formula_examples (formula_id, example_title, example_problem, given_values, solution_steps, final_answer, difficulty_level) VALUES
        (bayes_formula_id, 
         'Medical Test Example',
         'A medical test is 99% accurate. The disease affects 1% of the population. If someone tests positive, what is the probability they actually have the disease?',
         '{"P(Test+|Disease)": 0.99, "P(Disease)": 0.01, "P(Test+|No Disease)": 0.01}',
         'Step 1: Calculate P(Test+) using total probability\nStep 2: Apply Bayes theorem\nStep 3: P(Disease|Test+) = P(Test+|Disease) × P(Disease) / P(Test+)',
         '0.5 or 50%',
         'intermediate')
        ON CONFLICT DO NOTHING;
        
        -- Insert prerequisites
        INSERT INTO formula_prerequisites (formula_id, prerequisite_concept, importance_level, description) VALUES
        (bayes_formula_id, 'Conditional Probability', 'critical', 'Must understand P(A|B) notation and meaning'),
        (bayes_formula_id, 'Total Probability Rule', 'high', 'Often needed to calculate P(A) when not directly given')
        ON CONFLICT DO NOTHING;
        
        RAISE NOTICE 'Enhanced data inserted for Bayes Theorem (formula_id: %)', bayes_formula_id;
    ELSE
        RAISE NOTICE 'Bayes Theorem formula not found - skipping sample data insertion';
    END IF;
END $$;

-- ============================================================================
-- PHASE 5: Verification queries
-- ============================================================================

-- Verify new tables were created
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE tablename IN ('formula_variables', 'formula_relationships', 'formula_keywords', 'formula_examples', 'formula_prerequisites')
ORDER BY tablename;

-- Verify new columns were added
SELECT 
    column_name,
    data_type,
    is_nullable
FROM information_schema.columns 
WHERE table_name = 'formula' 
    AND column_name IN ('category', 'difficulty_level', 'assumptions', 'formula_expression', 'output_target')
ORDER BY column_name;

-- Count records in new tables
SELECT 
    'formula_variables' as table_name, COUNT(*) as record_count FROM formula_variables
UNION ALL
SELECT 
    'formula_relationships' as table_name, COUNT(*) as record_count FROM formula_relationships
UNION ALL
SELECT 
    'formula_keywords' as table_name, COUNT(*) as record_count FROM formula_keywords
UNION ALL
SELECT 
    'formula_examples' as table_name, COUNT(*) as record_count FROM formula_examples
UNION ALL
SELECT 
    'formula_prerequisites' as table_name, COUNT(*) as record_count FROM formula_prerequisites;

-- ============================================================================
-- Migration Complete
-- ============================================================================

SELECT 'Enhanced schema migration completed successfully!' as status;
