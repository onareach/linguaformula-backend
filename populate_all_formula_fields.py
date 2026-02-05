#!/usr/bin/env python3
"""
Populate formula fields (english_verbalization, symbolic_verbalization, units, example,
historical_context) for all formulas in tbl_formula per POPULATE_FORMULA_FIELDS_INSTRUCTIONS.md.
Run against local development database by default.
"""
import os
import sys
import getpass
import psycopg2

# Get database URL from environment or use defaults for local dev
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    DB_NAME = os.environ.get("DB_NAME", "linguaformula")
    DB_USER = os.environ.get("DB_USER", "dev_user")
    DB_PASSWORD = os.environ.get("DB_PASSWORD") or os.environ.get("PGPASSWORD")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    if not DB_PASSWORD:
        # Local dev default (same as app.py and other backend scripts)
        DB_PASSWORD = os.environ.get("DB_PASSWORD", "dev123")
    if not DB_PASSWORD:
        try:
            DB_PASSWORD = getpass.getpass(f"Password for database user '{DB_USER}': ")
        except (EOFError, KeyboardInterrupt):
            print("❌ Password required. Set PGPASSWORD or DB_PASSWORD.")
            sys.exit(1)
    DATABASE_URL = f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"

# Dimensionless / notation stub for formulas that have no physical units
DIMENSIONLESS = "Dimensionless; this formula describes counts, probabilities, or mathematical/set-theoretic structure rather than physical quantities with units."

# All formula updates: formula_id -> (english_verbalization, symbolic_verbalization, units, example, historical_context)
FORMULA_UPDATES = [
    {
        "formula_id": 1,
        "english_verbalization": "Momentum equals mass times velocity.",
        "symbolic_verbalization": 'Pronunciation examples: "p equals m v" or "Momentum equals mass times velocity" or "p vector equals m times v vector".',
        "units": "SI units: kilogram meters per second (kg·m/s). Alternative units: gram centimeters per second (g·cm/s) in CGS system, or slug feet per second (slug·ft/s) in imperial system.",
        "example": "If a 5 kg cart moves at 2 m/s, the momentum is: p = m × v = 5 kg × 2 m/s = 10 kg·m/s.",
        "historical_context": "The concept of momentum (quantity of motion) was developed by Isaac Newton (1643–1727) and appears in his Principia (1687). Newton used it to state the laws of motion and conservation of momentum in a closed system, enabling the analysis of collisions and dynamics.",
    },
    {
        "formula_id": 34,
        "english_verbalization": "The momentum of object one initially plus the momentum of object two initially equals the momentum of object one finally plus the momentum of object two finally.",
        "symbolic_verbalization": 'Pronunciation examples: "p one initial plus p two initial equals p one final plus p two final" or "Total initial momentum equals total final momentum" or "p sub one i plus p sub two i equals p sub one f plus p sub two f".',
        "units": "SI units: kilogram meters per second (kg·m/s) for each momentum term; the equation is dimensionally consistent. Alternative units: g·cm/s (CGS) or slug·ft/s (imperial).",
        "example": "If two carts of mass 2 kg and 3 kg move toward each other at 4 m/s and 1 m/s and stick together, total momentum before = 2×4 − 3×1 = 5 kg·m/s; after collision the combined 5 kg mass has velocity 1 m/s, so total momentum after = 5×1 = 5 kg·m/s.",
        "historical_context": "Conservation of momentum was formulated by Isaac Newton (1643–1727) in his Principia (1687) as a consequence of his third law. It became a cornerstone of classical mechanics and is used to analyze collisions and isolated systems.",
    },
    {
        "formula_id": 35,
        "english_verbalization": "Kinetic energy equals one-half times mass times velocity squared.",
        "symbolic_verbalization": 'Pronunciation examples: "E equals one-half m v squared" or "Kinetic energy equals one-half times mass times velocity squared" or "E sub kinetic equals one-half m v squared".',
        "units": "SI units: Joules (J) or kg·m²/s². Alternative units: ergs (g·cm²/s²) in CGS system, or foot-pounds (ft·lb) in imperial system.",
        "example": "If a bicycle weighing 20 kg is moving at 3 meters per second, the kinetic energy is calculated as: E = (1/2) × m × v² = (1/2) × 20 kg × (3 m/s)² = (1/2) × 20 × 9 = 90 J.",
        "historical_context": "The concept of kinetic energy (originally called 'vis viva' or 'living force') was first proposed by Gottfried Wilhelm Leibniz (1646-1716) around 1686. Leibniz initially proposed mv² as the measure of 'living force', but the modern form E = (1/2)mv² with the factor of 1/2 was established in the 19th century through the work-energy theorem. The formula was developed to quantify the energy of motion and solve problems in mechanics, particularly in understanding collisions and the conservation of energy in physical systems.",
    },
    {
        "formula_id": 36,
        "english_verbalization": "Potential energy equals mass times gravitational acceleration times height.",
        "symbolic_verbalization": 'Pronunciation examples: "E equals m g h" or "Potential energy equals mass times g times height" or "E sub potential equals m g h".',
        "units": "SI units: Joules (J) or kg·m²/s². Alternative units: ergs (g·cm²/s²) in CGS system, or foot-pounds (ft·lb) in imperial system.",
        "example": "If a 10 kg textbook is lifted 2 meters above the floor (g ≈ 9.8 m/s²), the gravitational potential energy is: E = m × g × h = 10 kg × 9.8 m/s² × 2 m = 196 J.",
        "historical_context": "Gravitational potential energy in the form mgh emerged from the work of Galileo (1564–1642) on falling bodies and was formalized within the broader concept of mechanical energy by physicists in the 18th and 19th centuries, including in the development of the work-energy theorem and conservation of energy.",
    },
    {
        "formula_id": 2,
        "english_verbalization": "Force equals mass times acceleration.",
        "symbolic_verbalization": 'Pronunciation examples: "F equals m a" or "Force equals mass times acceleration" or "F equals m times a".',
        "units": "SI units: Newtons (N) or kg·m/s². Alternative units: dynes (g·cm/s²) in CGS system, or pounds-force (lbf) in imperial system.",
        "example": "If a car with a mass of 1200 kg accelerates at 2 m/s², the force is: F = m × a = 1200 kg × 2 m/s² = 2400 N.",
        "historical_context": "Newton's second law of motion was formulated by Isaac Newton (1643–1727) and published in his 'Philosophiæ Naturalis Principia Mathematica' in 1687. The law was developed to describe the relationship between force, mass, and acceleration, providing a mathematical foundation for classical mechanics.",
    },
    {
        "formula_id": 3,
        "english_verbalization": "Energy equals mass times the speed of light squared.",
        "symbolic_verbalization": 'Pronunciation examples: "E equals m c squared" or "Energy equals mass times the speed of light squared" or "E equals m c squared".',
        "units": "SI units: Joules (J). Mass in kg, c ≈ 2.998×10⁸ m/s, so E in kg·m²/s² = J. Alternative units: electron volts (eV) or ergs in CGS.",
        "example": "If 1 gram (0.001 kg) of mass were converted entirely to energy: E = m c² = 0.001 kg × (2.998×10⁸ m/s)² ≈ 8.99×10¹³ J.",
        "historical_context": "Mass-energy equivalence was proposed by Albert Einstein (1879–1955) in 1905 as part of his special theory of relativity. The formula showed that mass and energy are interchangeable, with profound implications for nuclear physics and cosmology.",
    },
    {
        "formula_id": 67,
        "english_verbalization": "Euler's number e equals the limit as n approaches infinity of the quantity one plus one over n, all raised to the power of n, which is approximately 2.71828.",
        "symbolic_verbalization": 'Pronunciation examples: "e equals the limit as n goes to infinity of one plus one over n to the n" or "e is approximately 2.71828" or "e equals lim of one plus one over n, quantity to the n".',
        "units": "Dimensionless; e is a pure mathematical constant with no physical units.",
        "example": "For n = 1000, (1 + 1/1000)^1000 ≈ 2.7169; for n = 1,000,000, (1 + 1/1000000)^1000000 ≈ 2.71828, approaching e.",
        "historical_context": "The constant e was studied by Jacob Bernoulli (1655–1705) in connection with compound interest (1683). Leonhard Euler (1707–1783) denoted it by e and showed its role as the base of natural logarithms and in the limit (1 + 1/n)^n.",
    },
    {
        "formula_id": 133,
        "english_verbalization": "The size of the population is represented by n.",
        "symbolic_verbalization": 'Pronunciation examples: "n" or "population size is n" or "n is the size of the population".',
        "units": DIMENSIONLESS,
        "example": "If we intend to take samples from a bucket of 50 parts, n = 50.",
        "historical_context": "The use of n for population or sample size is standard notation in statistics and combinatorics, widely adopted in 20th-century textbooks and research.",
    },
    {
        "formula_id": 134,
        "english_verbalization": "The size of a sample is represented by r.",
        "symbolic_verbalization": 'Pronunciation examples: "r" or "sample size is r" or "r is the size of the sample".',
        "units": DIMENSIONLESS,
        "example": "If we take a sample of 5 parts from a bucket of parts, r = 5.",
        "historical_context": "The use of r for sample size (or number of objects chosen) is standard in combinatorics and statistics, especially in permutation and combination formulas.",
    },
    {
        "formula_id": 135,
        "english_verbalization": "The number of ways to arrange n objects is n factorial.",
        "symbolic_verbalization": 'Pronunciation examples: "n factorial" or "the number of arrangements of n objects is n factorial" or "n exclamation point".',
        "units": DIMENSIONLESS,
        "example": "The number of ways to arrange 5 distinct cards in a row is 5! = 5 × 4 × 3 × 2 × 1 = 120.",
        "historical_context": "Factorial notation and its use in counting arrangements date back to the development of combinatorics; the symbol n! was introduced by Christian Kramp (1760–1826) in 1808.",
    },
    {
        "formula_id": 143,
        "english_verbalization": "The number of permutations of r distinct objects selected from n, where order matters, equals n factorial divided by the quantity n minus r factorial.",
        "symbolic_verbalization": 'Pronunciation examples: "P of n comma r equals n factorial over n minus r factorial" or "Permutations of r from n equals n factorial divided by n minus r factorial" or "P n r equals n factorial over n minus r factorial".',
        "units": DIMENSIONLESS,
        "example": "The number of ordered 5-card sequences from a 52-card deck is P(52,5) = 52!/(52−5)! = 52!/47! = 52×51×50×49×48 = 311,875,200.",
        "historical_context": "Permutation counting was developed in combinatorics; the notation P(n,r) or P_r^n is standard in statistics and discrete mathematics.",
    },
    {
        "formula_id": 169,
        "english_verbalization": "The number of permutations of n objects with repeated types equals n factorial divided by the product of n sub one factorial times n sub two factorial times dot dot dot times n sub r factorial.",
        "symbolic_verbalization": 'Pronunciation examples: "N equals n factorial over n one factorial times n two factorial times dot dot dot times n r factorial" or "Permutations with repetition: n factorial divided by the product of the factorials of the counts" or "N equals n factorial over product of n sub i factorial".',
        "units": DIMENSIONLESS,
        "example": "The number of distinct arrangements of the letters in BALLOON (7 letters: 1 B, 1 A, 2 L, 2 O, 1 N) is 7!/(1!×1!×2!×2!×1!) = 5040/4 = 1260.",
        "historical_context": "The formula for permutations with repeated elements is a standard result in combinatorics, used in probability and discrete mathematics.",
    },
    {
        "formula_id": 142,
        "english_verbalization": "The number of combinations of r objects chosen from n, where order does not matter, equals n factorial divided by the product of r factorial times the quantity n minus r factorial.",
        "symbolic_verbalization": 'Pronunciation examples: "C of n comma r equals n choose r equals n factorial over r factorial times n minus r factorial" or "Combinations of r from n" or "n choose r".',
        "units": DIMENSIONLESS,
        "example": "The number of 5-card hands from a 52-card deck is C(52,5) = 52!/(5!×47!) = 2,598,960.",
        "historical_context": "Binomial coefficients (n choose r) were studied by Blaise Pascal (1623–1662) and appear in Pascal's triangle; the notation C(n,r) or (n choose r) is standard in combinatorics and statistics.",
    },
    {
        "formula_id": 144,
        "english_verbalization": "The sample space is represented by S.",
        "symbolic_verbalization": 'Pronunciation examples: "S" or "sample space S" or "S is the sample space".',
        "units": DIMENSIONLESS,
        "example": "For one fair die roll, S = {1, 2, 3, 4, 5, 6}.",
        "historical_context": "Sample space is fundamental in probability theory; the notation S was popularized in 20th-century probability and statistics textbooks.",
    },
    {
        "formula_id": 145,
        "english_verbalization": "An individual outcome may be represented by x, s, or omega.",
        "symbolic_verbalization": 'Pronunciation examples: "x, s, or omega" or "an outcome is denoted x, s, or omega" or "individual outcome: x, s, or omega".',
        "units": DIMENSIONLESS,
        "example": "If S = {a, b, c}, one outcome might be s = a.",
        "historical_context": "The use of x, s, and ω (omega) for outcomes is standard in probability theory; ω is common in measure-theoretic treatment.",
    },
    {
        "formula_id": 100,
        "english_verbalization": "The sample space S equals the set of all positive real numbers, which is the set of all x such that x is greater than zero.",
        "symbolic_verbalization": 'Pronunciation examples: "S equals R plus equals the set of x such that x is greater than zero" or "S is the positive reals" or "S equals the set of all positive real numbers".',
        "units": DIMENSIONLESS,
        "example": "If we measure a positive quantity (e.g., lifetime, length), S = ℝ⁺ = { x | x > 0 }.",
        "historical_context": "Positive real line as sample space is standard in continuous probability (e.g., lifetimes, amounts).",
    },
    {
        "formula_id": 146,
        "english_verbalization": "An event is represented by E.",
        "symbolic_verbalization": 'Pronunciation examples: "E" or "event E" or "E is an event".',
        "units": DIMENSIONLESS,
        "example": "For three coin flips, the event 'exactly two heads' is E = {THH, HTH, HHT}.",
        "historical_context": "Event as a subset of the sample space is central to Kolmogorov's axiomatic probability (1933) and modern statistics.",
    },
    {
        "formula_id": 148,
        "english_verbalization": "The union of events E sub one and E sub two is represented by E sub one union E sub two.",
        "symbolic_verbalization": 'Pronunciation examples: "E one union E two" or "the union of E one and E two" or "E sub one cup E sub two".',
        "units": DIMENSIONLESS,
        "example": "If E₁ = {1,2} and E₂ = {2,3}, then E₁ ∪ E₂ = {1,2,3}.",
        "historical_context": "Union of events and set-theoretic notation (∪) in probability were formalized in 20th-century probability theory.",
    },
    {
        "formula_id": 149,
        "english_verbalization": "The intersection of events E sub one and E sub two is represented by E sub one intersect E sub two.",
        "symbolic_verbalization": 'Pronunciation examples: "E one intersect E two" or "the intersection of E one and E two" or "E sub one cap E sub two".',
        "units": DIMENSIONLESS,
        "example": "If E₁ = {1,2} and E₂ = {2,3}, then E₁ ∩ E₂ = {2}.",
        "historical_context": "Intersection of events is standard set-theoretic probability; notation ∩ from set theory.",
    },
    {
        "formula_id": 150,
        "english_verbalization": "The complement of event E is represented by E prime.",
        "symbolic_verbalization": 'Pronunciation examples: "E prime" or "the complement of E" or "E complement".',
        "units": DIMENSIONLESS,
        "example": "If S = {1,2,3,4,5} and E = {1,2}, then E' = {3,4,5}.",
        "historical_context": "Complement of an event is fundamental in probability; notation E' or E^c is standard.",
    },
    {
        "formula_id": 151,
        "english_verbalization": "Events A and B are mutually exclusive if and only if the intersection of A and B equals the empty set.",
        "symbolic_verbalization": 'Pronunciation examples: "A intersect B equals the empty set" or "A and B are mutually exclusive" or "A cap B equals empty set".',
        "units": DIMENSIONLESS,
        "example": "When rolling one die, the event 'roll 1' and the event 'roll 2' are mutually exclusive: {1} ∩ {2} = ∅.",
        "historical_context": "Mutually exclusive events are a core concept in probability; the term and formal definition appear in standard probability texts.",
    },
    {
        "formula_id": 152,
        "english_verbalization": "The complement of the complement of E equals E.",
        "symbolic_verbalization": 'Pronunciation examples: "E prime prime equals E" or "the complement of the complement of E is E" or "double complement of E equals E".',
        "units": DIMENSIONLESS,
        "example": "If E = {1,2} and S = {1,2,3}, then (E')' = (S∖E)' = E.",
        "historical_context": "Double complement law is a basic law of set theory, attributed to the development of Boolean algebra and set theory in the 19th and early 20th centuries.",
    },
    {
        "formula_id": 154,
        "english_verbalization": "The intersection of the union of A and B with C equals the union of the intersection of A and C with the intersection of B and C.",
        "symbolic_verbalization": 'Pronunciation examples: "A union B intersect C equals A intersect C union B intersect C" or "intersection distributes over union" or "A cup B cap C equals A cap C cup B cap C".',
        "units": DIMENSIONLESS,
        "example": "For sets A, B, C: (A∪B)∩C = (A∩C)∪(B∩C), analogous to c(a+b) = ca+cb in algebra.",
        "historical_context": "Distributive laws for sets are part of Boolean algebra and set theory, developed in the 19th century (e.g., George Boole).",
    },
    {
        "formula_id": 157,
        "english_verbalization": "The union of the intersection of A and B with C equals the intersection of the union of A and C with the union of B and C.",
        "symbolic_verbalization": 'Pronunciation examples: "A intersect B union C equals A union C intersect B union C" or "union distributes over intersection" or "A cap B cup C equals A cup C cap B cup C".',
        "units": DIMENSIONLESS,
        "example": "For sets A, B, C: (A∩B)∪C = (A∪C)∩(B∪C).",
        "historical_context": "Distributive law of union over intersection is a standard set-theoretic identity in Boolean algebra.",
    },
    {
        "formula_id": 158,
        "english_verbalization": "The complement of the union of A and B equals the intersection of the complement of A and the complement of B.",
        "symbolic_verbalization": 'Pronunciation examples: "A union B complement equals A complement intersect B complement" or "De Morgan: complement of union is intersection of complements" or "A cup B prime equals A prime cap B prime".',
        "units": DIMENSIONLESS,
        "example": "If A = {1}, B = {2}, S = {1,2,3}, then (A∪B)' = {3} and A'∩B' = {3}∩{1,3} = {3}.",
        "historical_context": "De Morgan's laws are named after Augustus De Morgan (1806–1871), who stated them for logic and set theory.",
    },
    {
        "formula_id": 159,
        "english_verbalization": "The complement of the intersection of A and B equals the union of the complement of A and the complement of B.",
        "symbolic_verbalization": 'Pronunciation examples: "A intersect B complement equals A complement union B complement" or "De Morgan: complement of intersection is union of complements" or "A cap B prime equals A prime cup B prime".',
        "units": DIMENSIONLESS,
        "example": "If A = {1,2}, B = {2,3}, S = {1,2,3}, then (A∩B)' = {1,3} and A'∪B' = {3}∪{1} = {1,3}.",
        "historical_context": "De Morgan's second law (complement of intersection equals union of complements) is attributed to Augustus De Morgan (1806–1871).",
    },
    {
        "formula_id": 165,
        "english_verbalization": "The total number of outcomes N equals n sub one times n sub two times dot dot dot times n sub k.",
        "symbolic_verbalization": 'Pronunciation examples: "N equals n one times n two times dot dot dot times n k" or "Multiplication rule: total ways is the product of ways at each step" or "N equals product of n sub i".',
        "units": DIMENSIONLESS,
        "example": "With 3 shirts and 2 pants, the number of shirt-pant outfits is N = 3 × 2 = 6.",
        "historical_context": "The multiplication rule for counting is a fundamental principle in combinatorics, taught in introductory probability and statistics.",
    },
    {
        "formula_id": 170,
        "english_verbalization": "The probability of event E is represented by P of E.",
        "symbolic_verbalization": 'Pronunciation examples: "P of E" or "probability of E" or "P E".',
        "units": "Probability is dimensionless (a number between 0 and 1, or 0% and 100%).",
        "example": "For a fair die, P(rolling 4) = 1/6.",
        "historical_context": "The notation P(E) for probability of an event was popularized in 20th-century axiomatic probability (Kolmogorov, 1933) and statistics.",
    },
    {
        "formula_id": 171,
        "english_verbalization": "The probability of each equally likely outcome equals one divided by N.",
        "symbolic_verbalization": 'Pronunciation examples: "one over N" or "each outcome has probability one over N" or "probability equals one divided by N".',
        "units": "Dimensionless (probability).",
        "example": "When rolling a fair die, N = 6 equally likely outcomes, so each has probability 1/6.",
        "historical_context": "Equally likely outcomes and the 1/N rule form the classical definition of probability, dating to early probability theory (e.g., Laplace).",
    },
    {
        "formula_id": 172,
        "english_verbalization": "The probability of event A equals the number of favorable outcomes divided by the total number of possible outcomes, which equals s divided by n.",
        "symbolic_verbalization": 'Pronunciation examples: "P of A equals s over n" or "probability of A equals favorable over total" or "P A equals number of favorable over number of possible".',
        "units": "Dimensionless (probability).",
        "example": "The probability of drawing one specific diode from 100 is P(A) = 1/100 = 0.01, where s = 1 and n = 100.",
        "historical_context": "The classical probability formula P(A) = (number of favorable)/(number of possible) for equally likely outcomes is attributed to Laplace and classical probability.",
    },
    {
        "formula_id": 176,
        "english_verbalization": "The probability of event E equals the probability of a sub one plus the probability of a sub two plus dot dot dot plus the probability of a sub k.",
        "symbolic_verbalization": 'Pronunciation examples: "P of E equals P of a one plus P of a two plus dot dot dot plus P of a k" or "probability of E is the sum of probabilities of its outcomes" or "P E equals sum of P a i".',
        "units": "Dimensionless (probability).",
        "example": "If outcomes a, b, c have P(a)=0.1, P(b)=0.3, P(c)=0.3, then P({a,b}) = 0.1 + 0.3 = 0.4.",
        "historical_context": "Addition of probabilities for disjoint outcomes is part of the axiomatic definition of probability (Kolmogorov, 1933).",
    },
    {
        "formula_id": 177,
        "english_verbalization": "The probability of event A equals the number of times A occurred divided by the number of times the procedure was repeated.",
        "symbolic_verbalization": 'Pronunciation examples: "P of A equals number of times A occurred over number of trials" or "relative frequency of A" or "P A equals count of A over number of repetitions".',
        "units": "Dimensionless (probability).",
        "example": "If a coin is flipped 1000 times and heads appears 503 times, the relative frequency approximation is P(heads) ≈ 503/1000 = 0.503.",
        "historical_context": "Relative frequency as an approximation of probability is the frequentist interpretation of probability, developed in statistics and applied widely in the 20th century.",
    },
    {
        "formula_id": 179,
        "english_verbalization": "The probability of the union of A and B equals the probability of A plus the probability of B minus the probability of the intersection of A and B.",
        "symbolic_verbalization": 'Pronunciation examples: "P of A union B equals P of A plus P of B minus P of A intersect B" or "addition rule for union" or "P A cup B equals P A plus P B minus P A cap B".',
        "units": "Dimensionless (probability).",
        "example": "If P(A)=0.5, P(B)=0.4, P(A∩B)=0.2, then P(A∪B) = 0.5 + 0.4 − 0.2 = 0.7.",
        "historical_context": "The inclusion-exclusion formula for two events is a standard result in probability, following from the axioms and set theory.",
    },
    {
        "formula_id": 181,
        "english_verbalization": "If the intersection of A and B equals the empty set, then the probability of the intersection of A and B equals zero.",
        "symbolic_verbalization": 'Pronunciation examples: "If A and B are mutually exclusive, then P of A intersect B equals zero" or "mutually exclusive implies probability of intersection is zero" or "A cap B empty then P A cap B equals zero".',
        "units": "Dimensionless (probability).",
        "example": "For one die roll, P(rolling 1 and rolling 2) = P(∅) = 0.",
        "historical_context": "Probability of the empty set is zero by the axioms of probability; mutually exclusive events have empty intersection.",
    },
    {
        "formula_id": 184,
        "english_verbalization": "The probability of B given A equals the probability of the intersection of A and B divided by the probability of A, which also equals the number of outcomes in the intersection of A and B divided by the number of outcomes in A.",
        "symbolic_verbalization": 'Pronunciation examples: "P of B given A equals P of A intersect B over P of A" or "conditional probability of B given A" or "P B given A equals P A cap B over P A".',
        "units": "Dimensionless (probability).",
        "example": "If P(A)=0.4 and P(A∩B)=0.1, then P(B|A) = 0.1/0.4 = 0.25.",
        "historical_context": "Conditional probability P(B|A) = P(A∩B)/P(A) is a definition that appears in axiomatic probability and Bayesian statistics.",
    },
    {
        "formula_id": 185,
        "english_verbalization": "The probability of the intersection of A and B equals the probability of B given A times the probability of A, which also equals the probability of A given B times the probability of B.",
        "symbolic_verbalization": 'Pronunciation examples: "P of A intersect B equals P of B given A times P of A" or "multiplication rule for dependent events" or "P A cap B equals P B given A times P A".',
        "units": "Dimensionless (probability).",
        "example": "From a bag with 5 green and 7 red marbles, P(green first and red second) = (5/12)×(7/11) ≈ 0.265.",
        "historical_context": "The multiplication rule P(A∩B) = P(B|A)P(A) is a direct consequence of the definition of conditional probability and is central to Bayesian reasoning.",
    },
    {
        "formula_id": 187,
        "english_verbalization": "The probability of B equals the probability of the intersection of B and A plus the probability of the intersection of B and the complement of A, which equals the probability of B given A times the probability of A plus the probability of B given the complement of A times the probability of the complement of A.",
        "symbolic_verbalization": 'Pronunciation examples: "P of B equals P of B given A times P of A plus P of B given A complement times P of A complement" or "law of total probability" or "P B equals P B given A P A plus P B given A prime P A prime".',
        "units": "Dimensionless (probability).",
        "example": "P(Failure) = P(F|High)×P(High) + P(F|Low)×P(Low) = 0.1×0.2 + 0.005×0.8 = 0.02 + 0.004 = 0.024.",
        "historical_context": "The law of total probability (total probability rule) is a fundamental identity in probability, used in Bayesian inference and decision theory.",
    },
    {
        "formula_id": 190,
        "english_verbalization": "The probability of the intersection of L and R equals the probability of L times the probability of R.",
        "symbolic_verbalization": 'Pronunciation examples: "P of L and R equals P of L times P of R" or "for independent components in series, probability both work is product" or "P L cap R equals P L times P R".',
        "units": "Dimensionless (probability).",
        "example": "If P(L)=0.8 and P(R)=0.9 for two independent series components, P(both work) = 0.8 × 0.9 = 0.72.",
        "historical_context": "For independent events, P(A∩B) = P(A)P(B); applied to reliability of series systems in engineering and statistics.",
    },
    {
        "formula_id": 191,
        "english_verbalization": "The probability of the union of T and B equals the probability of T plus the probability of B minus the probability of the intersection of T and B.",
        "symbolic_verbalization": 'Pronunciation examples: "P of T union B equals P of T plus P of B minus P of T intersect B" or "at least one works: use addition rule" or "P T cup B equals P T plus P B minus P T cap B".',
        "units": "Dimensionless (probability).",
        "example": "If P(T)=0.95 and P(B)=0.9 (independent), P(T∩B)=0.855, so P(at least one works) = 0.95 + 0.9 − 0.855 = 0.995.",
        "historical_context": "Probability that at least one of two independent components works uses the addition rule; standard in reliability and probability.",
    },
    {
        "formula_id": 192,
        "english_verbalization": "The probability that none are contaminated equals the quantity one minus p raised to the power of n.",
        "symbolic_verbalization": 'Pronunciation examples: "P none contaminated equals one minus p to the n" or "probability all n are clean is one minus p to the n" or "one minus p raised to n".',
        "units": "Dimensionless (probability).",
        "example": "If p = 0.11 and n = 5, P(none contaminated) = (1 − 0.11)^5 = (0.89)^5 ≈ 0.558.",
        "historical_context": "Probability of zero successes in n independent Bernoulli trials is (1−p)^n; standard in quality control and binomial settings.",
    },
    {
        "formula_id": 193,
        "english_verbalization": "The probability mass function p of x equals the probability that the random variable X equals x.",
        "symbolic_verbalization": 'Pronunciation examples: "p of x equals P of X equals x" or "PMF of x is the probability that X equals x" or "p x equals P X equals x".',
        "units": "Dimensionless (probability per outcome).",
        "example": "For a fair die, p(3) = P(X=3) = 1/6.",
        "historical_context": "Probability mass function (PMF) is standard in discrete probability and mathematical statistics; the term dates to 20th-century probability theory.",
    },
    {
        "formula_id": 197,
        "english_verbalization": "The cumulative distribution function F of x equals the probability that X is less than or equal to x, which equals the integral from negative infinity to x of f of t with respect to t.",
        "symbolic_verbalization": 'Pronunciation examples: "F of x equals P of X less than or equal to x equals the integral from negative infinity to x of f of t d t" or "CDF is the integral of the PDF" or "F x equals integral of f t from minus infinity to x".',
        "units": "Dimensionless (probability); F(x) is in [0,1]. If f is a PDF, its integral has units of probability.",
        "example": "If f(t)=2t on [0,1], then F(0.6) = ∫₀^0.6 2t dt = t²|₀^0.6 = 0.36.",
        "historical_context": "The cumulative distribution function (CDF) is fundamental in probability and statistics; the integral definition for continuous variables is standard in measure-theoretic probability.",
    },
    {
        "formula_id": 198,
        "english_verbalization": "The mean mu equals the expected value of X, which equals the sum over all x of x times f of x.",
        "symbolic_verbalization": 'Pronunciation examples: "mu equals E of X equals the sum over x of x times f of x" or "expected value of X" or "mean equals sum of x times p of x".',
        "units": "Same units as the random variable X (e.g., meters if X is length). For counts, dimensionless.",
        "example": "If X takes values 0,1,2 with p(0)=0.2, p(1)=0.5, p(2)=0.3, then μ = 0×0.2 + 1×0.5 + 2×0.3 = 1.1.",
        "historical_context": "Expected value (mean) of a discrete random variable was formalized in probability theory and statistics; the notation E(X) or μ is standard.",
    },
    {
        "formula_id": 199,
        "english_verbalization": "The variance sigma squared equals the variance of X, which equals the sum over all x of the quantity x minus mu squared times f of x.",
        "symbolic_verbalization": 'Pronunciation examples: "sigma squared equals V of X equals sum over x of x minus mu squared times f of x" or "variance of X" or "sigma squared equals expected value of X minus mu squared".',
        "units": "Square of the units of X (e.g., m² if X is in meters). For counts, dimensionless.",
        "example": "For the distribution above (μ=1.1), σ² = (0−1.1)²×0.2 + (1−1.1)²×0.5 + (2−1.1)²×0.3 = 0.242 + 0.005 + 0.243 = 0.49.",
        "historical_context": "Variance as a measure of spread was developed in statistics; the formula Var(X) = E[(X−μ)²] is standard for discrete and continuous variables.",
    },
    {
        "formula_id": 202,
        "english_verbalization": "The standard deviation sigma equals the square root of sigma squared, which equals the square root of the variance of X.",
        "symbolic_verbalization": 'Pronunciation examples: "sigma equals the square root of sigma squared" or "standard deviation is the square root of variance" or "sigma equals square root of V of X".',
        "units": "Same units as X (e.g., meters). For counts, dimensionless.",
        "example": "If σ² = 0.49, then σ = √0.49 = 0.7.",
        "historical_context": "Standard deviation (square root of variance) was adopted in statistics to express spread in the same units as the variable; notation σ is standard.",
    },
    {
        "formula_id": 203,
        "english_verbalization": "The probability that X equals x equals the binomial coefficient of n choose x times p raised to the power of x times the quantity one minus p raised to the power of n minus x.",
        "symbolic_verbalization": 'Pronunciation examples: "P of X equals x equals n choose x times p to the x times one minus p to the n minus x" or "binomial probability" or "P X equals x equals binomial coefficient times p to x times one minus p to n minus x".',
        "units": "Dimensionless (probability).",
        "example": "For n=3, p=0.1, P(X=2) = C(3,2)×(0.1)²×(0.9)¹ = 3×0.01×0.9 = 0.027.",
        "historical_context": "The binomial distribution and formula were studied by Jacob Bernoulli (1655–1705) and others; it is the distribution of the number of successes in n independent Bernoulli trials.",
    },
    {
        "formula_id": 204,
        "english_verbalization": "The probability mass function f of x equals the binomial coefficient of n choose x times p raised to the power of x times the quantity one minus p raised to the power of n minus x, for x equals zero, one, dot dot dot, n.",
        "symbolic_verbalization": 'Pronunciation examples: "f of x equals n choose x times p to the x times one minus p to the n minus x, for x equals zero through n" or "binomial PMF" or "f x equals binomial coefficient p to x one minus p to n minus x".',
        "units": "Dimensionless (probability).",
        "example": "For 5 fair coin flips (n=5, p=0.5), f(2) = C(5,2)×(0.5)²×(0.5)³ = 10×0.25×0.125 = 0.3125.",
        "historical_context": "The binomial PMF gives the probability of exactly x successes in n trials; it is the standard model for counts of successes in fixed independent trials.",
    },
]


def run_updates():
    """Apply all formula field updates to the database."""
    conn = None
    try:
        db_url = DATABASE_URL.replace("postgres://", "postgresql://", 1) if DATABASE_URL.startswith("postgres://") else DATABASE_URL
        sslmode = "require" if DATABASE_URL.startswith("postgres://") else "disable"
        conn = psycopg2.connect(db_url, sslmode=sslmode)
        cur = conn.cursor()

        updated = 0
        for row in FORMULA_UPDATES:
            fid = row["formula_id"]
            cur.execute(
                """
                UPDATE tbl_formula
                SET english_verbalization = %s,
                    symbolic_verbalization = %s,
                    units = %s,
                    example = %s,
                    historical_context = %s
                WHERE formula_id = %s;
                """,
                (
                    row["english_verbalization"],
                    row["symbolic_verbalization"],
                    row["units"],
                    row["example"],
                    row["historical_context"],
                    fid,
                ),
            )
            if cur.rowcount:
                updated += 1
                print(f"  Updated formula_id={fid}")

        conn.commit()
        print("=" * 60)
        print(f"Done. Updated {updated} formula(s).")
        print("=" * 60)
        cur.close()
        conn.close()
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error: {e}")
        if conn:
            conn.rollback()
            conn.close()
        sys.exit(1)


if __name__ == "__main__":
    run_updates()
