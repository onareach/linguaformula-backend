-- Add English verbalizations to all formulas
-- Run with: PGPASSWORD=dev123 psql -d linguaformula -U dev_user -f migrations/add_english_verbalizations.sql
-- Or on Heroku: heroku pg:psql -a my-physics-formula-viewer-3x -f migrations/add_english_verbalizations.sql

-- Update formulas with English verbalizations
-- Only update if english_verbalization is NULL or empty string

-- Momentum
UPDATE formula 
SET english_verbalization = 'Momentum equals mass times velocity.'
WHERE id = 1 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Conservation of momentum
UPDATE formula 
SET english_verbalization = 'The momentum of object one initially plus the momentum of object two initially equals the momentum of object one finally plus the momentum of object two finally.'
WHERE id = 34 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Kinetic energy
UPDATE formula 
SET english_verbalization = 'Kinetic energy equals one-half times mass times velocity squared.'
WHERE id = 35 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Potential energy
UPDATE formula 
SET english_verbalization = 'Potential energy equals mass times gravitational acceleration times height.'
WHERE id = 36 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Newton's Second Law
UPDATE formula 
SET english_verbalization = 'Force equals mass times acceleration.'
WHERE id = 2 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Euler's Number
UPDATE formula 
SET english_verbalization = 'Euler''s number e equals the limit as n approaches infinity of the quantity one plus one over n, all raised to the power of n, which is approximately 2.71828.'
WHERE id = 67 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Mass-energy equivalence
UPDATE formula 
SET english_verbalization = 'Energy equals mass times the speed of light squared.'
WHERE id = 3 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Size of Population
UPDATE formula 
SET english_verbalization = 'The size of the population is represented by n.'
WHERE id = 133 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Size of a Sample
UPDATE formula 
SET english_verbalization = 'The size of a sample is represented by r.'
WHERE id = 134 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Number of Ways to Arrange n Objects
UPDATE formula 
SET english_verbalization = 'The number of ways to arrange n objects is n factorial.'
WHERE id = 135 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Permutations: P(n,r)
UPDATE formula 
SET english_verbalization = 'The number of permutations of r distinct objects selected from n, where order matters, equals n factorial divided by the quantity n minus r factorial.'
WHERE id = 143 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Permutations with Repeated Types
UPDATE formula 
SET english_verbalization = 'The number of permutations of n objects with repeated types equals n factorial divided by the product of n sub one factorial times n sub two factorial times dot dot dot times n sub r factorial.'
WHERE id = 169 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Combinations: C(n,r)
UPDATE formula 
SET english_verbalization = 'The number of combinations of r objects chosen from n, where order does not matter, equals n factorial divided by the product of r factorial times the quantity n minus r factorial.'
WHERE id = 142 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Sample Space
UPDATE formula 
SET english_verbalization = 'The sample space is represented by S.'
WHERE id = 144 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Sample: Individual Outcome
UPDATE formula 
SET english_verbalization = 'An individual outcome may be represented by x, s, or omega.'
WHERE id = 145 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Positive Real Sample Space
UPDATE formula 
SET english_verbalization = 'The sample space S equals the set of all positive real numbers, which is the set of all x such that x is greater than zero.'
WHERE id = 100 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Event
UPDATE formula 
SET english_verbalization = 'An event is represented by E.'
WHERE id = 146 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Events – Union
UPDATE formula 
SET english_verbalization = 'The union of events E sub one and E sub two is represented by E sub one union E sub two.'
WHERE id = 148 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Events – Intersection
UPDATE formula 
SET english_verbalization = 'The intersection of events E sub one and E sub two is represented by E sub one intersect E sub two.'
WHERE id = 149 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Event – Complement
UPDATE formula 
SET english_verbalization = 'The complement of event E is represented by E prime.'
WHERE id = 150 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Events – Mutually Exclusive
UPDATE formula 
SET english_verbalization = 'Events A and B are mutually exclusive if and only if the intersection of A and B equals the empty set.'
WHERE id = 151 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Double Complement Law
UPDATE formula 
SET english_verbalization = 'The complement of the complement of E equals E.'
WHERE id = 152 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Distributive Law of Intersection over Union
UPDATE formula 
SET english_verbalization = 'The intersection of the union of A and B with C equals the union of the intersection of A and C with the intersection of B and C.'
WHERE id = 154 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Distributive Law of Union over Intersection
UPDATE formula 
SET english_verbalization = 'The union of the intersection of A and B with C equals the intersection of the union of A and C with the union of B and C.'
WHERE id = 157 AND (english_verbalization IS NULL OR english_verbalization = '');

-- De Morgan's Law (1)
UPDATE formula 
SET english_verbalization = 'The complement of the union of A and B equals the intersection of the complement of A and the complement of B.'
WHERE id = 158 AND (english_verbalization IS NULL OR english_verbalization = '');

-- De Morgan's Law (2)
UPDATE formula 
SET english_verbalization = 'The complement of the intersection of A and B equals the union of the complement of A and the complement of B.'
WHERE id = 159 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Multiplication Rule
UPDATE formula 
SET english_verbalization = 'The total number of outcomes N equals n sub one times n sub two times dot dot dot times n sub k.'
WHERE id = 165 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability of an Event
UPDATE formula 
SET english_verbalization = 'The probability of event E is represented by P of E.'
WHERE id = 170 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability of Equally Likely Outcomes
UPDATE formula 
SET english_verbalization = 'The probability of each equally likely outcome equals one divided by N.'
WHERE id = 171 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability of Equally Likely Outcomes (2)
UPDATE formula 
SET english_verbalization = 'The probability of event A equals the number of favorable outcomes divided by the total number of possible outcomes, which equals s divided by n.'
WHERE id = 172 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Addition Rule for Discrete Probability
UPDATE formula 
SET english_verbalization = 'The probability of event E equals the probability of a sub one plus the probability of a sub two plus dot dot dot plus the probability of a sub k.'
WHERE id = 176 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Relative Frequency Approximation
UPDATE formula 
SET english_verbalization = 'The probability of event A equals the number of times A occurred divided by the number of times the procedure was repeated.'
WHERE id = 177 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Addition Rule for Unions
UPDATE formula 
SET english_verbalization = 'The probability of the union of A and B equals the probability of A plus the probability of B minus the probability of the intersection of A and B.'
WHERE id = 179 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Mutually Exclusive Events
UPDATE formula 
SET english_verbalization = 'If the intersection of A and B equals the empty set, then the probability of the intersection of A and B equals zero.'
WHERE id = 181 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Conditional Events
UPDATE formula 
SET english_verbalization = 'The probability of B given A equals the probability of the intersection of A and B divided by the probability of A, which also equals the number of outcomes in the intersection of A and B divided by the number of outcomes in A.'
WHERE id = 184 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Multiplication Rule for Conditional Events
UPDATE formula 
SET english_verbalization = 'The probability of the intersection of A and B equals the probability of B given A times the probability of A, which also equals the probability of A given B times the probability of B.'
WHERE id = 185 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Total Probability Rule
UPDATE formula 
SET english_verbalization = 'The probability of B equals the probability of the intersection of B and A plus the probability of the intersection of B and the complement of A, which equals the probability of B given A times the probability of A plus the probability of B given the complement of A times the probability of the complement of A.'
WHERE id = 187 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Success of Independent Series Components
UPDATE formula 
SET english_verbalization = 'The probability of the intersection of L and R equals the probability of L times the probability of R.'
WHERE id = 190 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Success of Independent Parallel Components
UPDATE formula 
SET english_verbalization = 'The probability of the union of T and B equals the probability of T plus the probability of B minus the probability of the intersection of T and B.'
WHERE id = 191 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Probability: Zero Contaminated Samples
UPDATE formula 
SET english_verbalization = 'The probability that none are contaminated equals the quantity one minus p raised to the power of n.'
WHERE id = 192 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Verify updates
SELECT id, formula_name, 
       CASE 
         WHEN english_verbalization IS NULL OR english_verbalization = '' THEN 'MISSING'
         ELSE 'HAS VERBALIZATION'
       END as verbalization_status,
       LENGTH(english_verbalization) as verbalization_length
FROM formula 
ORDER BY id;

-- Count formulas with and without verbalizations
SELECT 
  COUNT(*) FILTER (WHERE english_verbalization IS NULL OR english_verbalization = '') as missing_verbalizations,
  COUNT(*) FILTER (WHERE english_verbalization IS NOT NULL AND english_verbalization != '') as has_verbalizations,
  COUNT(*) as total_formulas
FROM formula;
