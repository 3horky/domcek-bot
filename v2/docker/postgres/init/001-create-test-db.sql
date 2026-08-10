SELECT 'CREATE DATABASE domcek_test OWNER domcek'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'domcek_test')\gexec
