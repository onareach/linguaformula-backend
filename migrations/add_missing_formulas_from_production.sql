-- Add formulas that exist in production but are missing in local development database
-- Run with: PGPASSWORD=dev123 psql -d linguaformula -U dev_user -f migrations/add_missing_formulas_from_production.sql

-- Probability Mass Function (PMF)
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  193,
  'Probability Mass Function (PMF)',
  'p(x) = P(X = x)',
  73,
  'The Probability Mass Function (PMF) describes the likelihood that a discrete random variable X will take on a specific value x. It answers the question: "What is the probability that X equals x?" This contrasts with the Cumulative Distribution Function (CDF), which gives the probability that X is within a range of values (instead of one specific value). The term "mass" reflects the notion that probability is concentrated at discrete points, with each point carrying a certain amount of probability weight.',
  'The probability mass function p of x equals the probability that the random variable X equals x.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Cumulative Distribution Function (CDF)
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  197,
  'Cumulative Distribution Function (CDF)',
  'F(x) = P(X \leq x) = \int_{-\infty}^{x} f(t)\,dt',
  80,
  'The Cumulative Distribution Function (CDF) gives the probability that a continuous random variable X is less than or equal to a specific value x. It is defined as the integral of the probability density function (PDF) from negative infinity up to x. While the integral symbolically begins at minus infinity, in many real-world cases (like height or age), the PDF is zero below a minimum value, so the accumulation effectively starts at that point. The CDF increases from 0 to 1 as x moves from the far left to the far right of the distribution. For example, suppose the PDF is f(t) = 2t on the interval from 0 to 1. To find the probability that X is less than or equal to 0.6, compute F(0.6) = integral from 0 to 0.6 of 2t dt = 0.36. This means there is a 36% chance that X falls at or below 0.6.',
  'The cumulative distribution function F of x equals the probability that X is less than or equal to x, which equals the integral from negative infinity to x of f of t with respect to t.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Mean (Or Expected Value) of a Discrete Random Variable
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  198,
  'Mean (Or Expected Value) of a Discrete Random Variable',
  '\mu = \mathrm{E}(X) = \sum_{x} x \cdot f(x)',
  100,
  'The mean of a discrete random variable X is a weighted average of the possible values of X with weights equal to each value''s probability.',
  'The mean mu equals the expected value of X, which equals the sum over all x of x times f of x.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Variance of a Discrete Random Variable
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  199,
  'Variance of a Discrete Random Variable',
  '\sigma^2 = V(X) = \sum_{x} (x - \mu)^2 \cdot f(x)',
  110,
  'The variance of a random variable X is a measure of dispersion or scatter in the possible values for X.',
  'The variance sigma squared equals the variance of X, which equals the sum over all x of the quantity x minus mu squared times f of x.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Standard Deviation of a Discrete Random Variable
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  202,
  'Standard Deviation of a Discrete Random Variable',
  '\sigma = \sqrt{\sigma^2} = \sqrt{V(X)}',
  120,
  'The standard deviation of a discrete random variable X is the square root of its variance. It measures how far values typically deviate from the mean.',
  'The standard deviation sigma equals the square root of sigma squared, which equals the square root of the variance of X.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Binomial Formula
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  203,
  'Binomial Formula',
  'P(X = x) = \binom{n}{x} (p)^x (1 - p)^{n - x}',
  130,
  'The binomial formula calculates the probability of getting exactly x successes in n independent trials, where each trial has a fixed probability p of success. For example, suppose p = 0.1 (probability of error), n = 3 (number of bits sent), and we want the probability of exactly 2 errors: P(X = 2) = C(3,2) * (0.1)^2 * (0.9)^1 = 3 * 0.01 * 0.9 = 0.027',
  'The probability that X equals x equals the binomial coefficient of n choose x times p raised to the power of x times the quantity one minus p raised to the power of n minus x.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Binomial Probability Mass Function (PMF)
INSERT INTO formula (id, formula_name, latex, display_order, formula_description, english_verbalization)
VALUES (
  204,
  'Binomial Probability Mass Function (PMF)',
  'f(x) = \binom{n}{x} p^x (1 - p)^{n - x}, \quad x = 0, 1, ..., n',
  140,
  'The binomial PMF (probability mass function gives the probability of getting exactly x successes in n independent trials, where each trial has probability p of success. This formula is used when counting how often a specific outcome occurs across repeated yes/no trials. For example, if you flip a coin 5 times, it can give you the probability of getting exactly 2 heads.',
  'The probability mass function f of x equals the binomial coefficient of n choose x times p raised to the power of x times the quantity one minus p raised to the power of n minus x, for x equals zero, one, dot dot dot, n.'
)
ON CONFLICT (id) DO UPDATE SET
  formula_name = EXCLUDED.formula_name,
  latex = EXCLUDED.latex,
  display_order = EXCLUDED.display_order,
  formula_description = EXCLUDED.formula_description,
  english_verbalization = EXCLUDED.english_verbalization;

-- Verify the insertions
SELECT 
  COUNT(*) as total_formulas,
  COUNT(*) FILTER (WHERE formula_description IS NOT NULL AND formula_description != '') as formulas_with_descriptions,
  COUNT(*) FILTER (WHERE english_verbalization IS NOT NULL AND english_verbalization != '') as formulas_with_verbalizations
FROM formula;
