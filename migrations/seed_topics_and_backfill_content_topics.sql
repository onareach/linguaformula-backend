-- Seed initial topics and backfill topic_handle for existing formulas/terms.
-- This script is safe to re-run.

INSERT INTO tbl_topic (topic_name, topic_handle)
VALUES
  ('Descriptive Statistics', 'descriptive_statistics'),
  ('Probability', 'probability'),
  ('Distributions', 'distributions'),
  ('Sampling and Inference', 'sampling_and_inference'),
  ('Classical Mechanics', 'classical_mechanics'),
  ('Relativity', 'relativity'),
  ('Mathematical Foundations', 'mathematical_foundations'),
  ('Uncategorized', 'uncategorized')
ON CONFLICT (topic_handle) DO NOTHING;

-- Formula backfill from primary discipline handle.
UPDATE tbl_formula f
SET topic_handle = t.topic_handle
FROM tbl_formula_discipline fd
JOIN tbl_discipline d ON d.discipline_id = fd.discipline_id
JOIN tbl_topic t ON
  (d.discipline_handle = 'statistics' AND t.topic_handle = 'descriptive_statistics') OR
  (d.discipline_handle = 'probability' AND t.topic_handle = 'probability') OR
  (d.discipline_handle = 'combinatorics' AND t.topic_handle = 'mathematical_foundations') OR
  (d.discipline_handle = 'classical_mechanics' AND t.topic_handle = 'classical_mechanics') OR
  (d.discipline_handle = 'relativity' AND t.topic_handle = 'relativity')
WHERE f.formula_id = fd.formula_id
  AND fd.formula_discipline_is_primary = true
  AND f.topic_handle IS NULL;

-- Term backfill from primary discipline handle.
UPDATE tbl_term tr
SET topic_handle = t.topic_handle
FROM tbl_term_discipline td
JOIN tbl_discipline d ON d.discipline_id = td.discipline_id
JOIN tbl_topic t ON
  (d.discipline_handle = 'statistics' AND t.topic_handle = 'descriptive_statistics') OR
  (d.discipline_handle = 'probability' AND t.topic_handle = 'probability') OR
  (d.discipline_handle = 'combinatorics' AND t.topic_handle = 'mathematical_foundations') OR
  (d.discipline_handle = 'classical_mechanics' AND t.topic_handle = 'classical_mechanics') OR
  (d.discipline_handle = 'relativity' AND t.topic_handle = 'relativity')
WHERE tr.term_id = td.term_id
  AND td.term_discipline_is_primary = true
  AND tr.topic_handle IS NULL;

-- Fallback for any remaining unmapped rows.
UPDATE tbl_formula
SET topic_handle = 'uncategorized'
WHERE topic_handle IS NULL;

UPDATE tbl_term
SET topic_handle = 'uncategorized'
WHERE topic_handle IS NULL;
