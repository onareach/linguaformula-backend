-- Add descriptions to formulas that are missing them
-- Run with: heroku pg:psql -a my-physics-formula-viewer-3x -f migrations/add_formula_descriptions.sql
-- Or locally: psql -d linguaformula -U dev_user -f migrations/add_formula_descriptions.sql

-- Update formulas with missing descriptions
-- Only update if description is NULL or empty string

-- Conservation of momentum
UPDATE formula 
SET formula_description = 'The law of conservation of momentum states that in a closed system with no external forces, the total momentum before a collision equals the total momentum after the collision. Momentum is conserved in both elastic and inelastic collisions.'
WHERE id = 34 AND (formula_description IS NULL OR formula_description = '');

-- Kinetic energy
UPDATE formula 
SET formula_description = 'Kinetic energy is the energy an object possesses due to its motion. It depends on the mass (m) of the object and the square of its velocity (v). The formula shows that kinetic energy increases quadratically with velocity, meaning doubling the speed quadruples the kinetic energy.'
WHERE id = 35 AND (formula_description IS NULL OR formula_description = '');

-- Potential energy
UPDATE formula 
SET formula_description = 'Potential energy is the stored energy an object has due to its position in a gravitational field. It depends on the mass (m) of the object, the acceleration due to gravity (g), and the height (h) above a reference point. This energy can be converted to kinetic energy as the object falls.'
WHERE id = 36 AND (formula_description IS NULL OR formula_description = '');

-- Newton's Second Law
UPDATE formula 
SET formula_description = 'Newton''s Second Law of Motion states that the force (F) acting on an object is equal to the mass (m) of the object multiplied by its acceleration (a). This fundamental law relates force, mass, and acceleration, showing that force causes acceleration, and more massive objects require more force to achieve the same acceleration.'
WHERE id = 2 AND (formula_description IS NULL OR formula_description = '');

-- Mass-energy equivalence
UPDATE formula 
SET formula_description = 'Einstein''s famous mass-energy equivalence formula shows that mass (m) and energy (E) are interchangeable, related by the speed of light squared (c²). This equation demonstrates that a small amount of mass can be converted into a tremendous amount of energy, as demonstrated in nuclear reactions.'
WHERE id = 3 AND (formula_description IS NULL OR formula_description = '');

-- Verify updates
SELECT id, formula_name, 
       CASE 
         WHEN formula_description IS NULL OR formula_description = '' THEN 'MISSING'
         ELSE 'HAS DESCRIPTION'
       END as description_status,
       LENGTH(formula_description) as desc_length
FROM formula 
WHERE id IN (2, 3, 34, 35, 36)
ORDER BY id;

-- Count formulas with and without descriptions
SELECT 
  COUNT(*) FILTER (WHERE formula_description IS NULL OR formula_description = '') as missing_descriptions,
  COUNT(*) FILTER (WHERE formula_description IS NOT NULL AND formula_description != '') as has_descriptions,
  COUNT(*) as total_formulas
FROM formula;
