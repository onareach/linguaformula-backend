-- Add Simple Linear Regression Model formula
-- Run with: heroku pg:psql -a my-physics-formula-viewer-3x -f migrations/add_simple_linear_regression.sql
-- Or locally: psql -d linguaformula -U dev_user -f migrations/add_simple_linear_regression.sql

-- Get the next display_order value
-- Insert the new formula
INSERT INTO formula (formula_name, latex, display_order, formula_description)
VALUES (
  'Simple Linear Regression Model',
  'y = \beta_0 + \beta_1 x + \epsilon',
  (SELECT COALESCE(MAX(display_order), 0) + 1 FROM formula),
  'Simple linear regression models the relationship between a dependent variable y and an independent variable x using a linear equation. β₀ is the y-intercept, β₁ is the slope, and ε represents the error term.'
)
ON CONFLICT DO NOTHING;

-- Verify the insertion
SELECT id, formula_name, latex, display_order 
FROM formula 
WHERE formula_name = 'Simple Linear Regression Model';
