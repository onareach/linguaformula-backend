-- Add English verbalizations for formulas missing in production
-- Run with: heroku pg:psql -a my-physics-formula-viewer-3x -f migrations/add_missing_verbalizations_production.sql

-- Probability Mass Function (PMF)
UPDATE formula 
SET english_verbalization = 'The probability mass function p of x equals the probability that the random variable X equals x.'
WHERE id = 193 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Cumulative Distribution Function (CDF)
UPDATE formula 
SET english_verbalization = 'The cumulative distribution function F of x equals the probability that X is less than or equal to x, which equals the integral from negative infinity to x of f of t with respect to t.'
WHERE id = 197 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Mean (Expected Value)
UPDATE formula 
SET english_verbalization = 'The mean mu equals the expected value of X, which equals the sum over all x of x times f of x.'
WHERE id = 198 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Variance
UPDATE formula 
SET english_verbalization = 'The variance sigma squared equals the variance of X, which equals the sum over all x of the quantity x minus mu squared times f of x.'
WHERE id = 199 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Standard Deviation
UPDATE formula 
SET english_verbalization = 'The standard deviation sigma equals the square root of sigma squared, which equals the square root of the variance of X.'
WHERE id = 202 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Binomial Formula
UPDATE formula 
SET english_verbalization = 'The probability that X equals x equals the binomial coefficient of n choose x times p raised to the power of x times the quantity one minus p raised to the power of n minus x.'
WHERE id = 203 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Binomial PMF
UPDATE formula 
SET english_verbalization = 'The probability mass function f of x equals the binomial coefficient of n choose x times p raised to the power of x times the quantity one minus p raised to the power of n minus x, for x equals zero, one, dot dot dot, n.'
WHERE id = 204 AND (english_verbalization IS NULL OR english_verbalization = '');

-- Verify
SELECT id, formula_name, 
       CASE 
         WHEN english_verbalization IS NULL OR english_verbalization = '' THEN 'MISSING'
         ELSE 'HAS VERBALIZATION'
       END as verbalization_status
FROM formula 
WHERE id IN (193, 197, 198, 199, 202, 203, 204)
ORDER BY id;

-- Final count
SELECT 
  COUNT(*) FILTER (WHERE english_verbalization IS NULL OR english_verbalization = '') as missing_verbalizations,
  COUNT(*) FILTER (WHERE english_verbalization IS NOT NULL AND english_verbalization != '') as has_verbalizations,
  COUNT(*) as total_formulas
FROM formula;
