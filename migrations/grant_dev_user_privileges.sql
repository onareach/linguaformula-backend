-- Grant necessary privileges to dev_user for schema changes
-- Run this ONCE as postgres user: sudo -u postgres psql -d linguaformula -f migrations/grant_dev_user_privileges.sql
-- Or: psql -U postgres -d linguaformula -f migrations/grant_dev_user_privileges.sql

-- Grant ALTER and other privileges on formula table
ALTER TABLE formula OWNER TO dev_user;

-- Grant privileges on all existing tables
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO dev_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO dev_user;

-- Grant privileges on future tables (default for new tables)
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO dev_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO dev_user;

-- Verify privileges
SELECT tableowner, tablename 
FROM pg_tables 
WHERE schemaname = 'public' 
  AND tablename IN ('formula', 'application', 'application_formula');
