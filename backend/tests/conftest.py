import os

# Unit tests must run without a local .env or a running database.
os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost:5432/smartdesk_test")
os.environ.setdefault("SECRET_KEY", "unit-test-signing-key-not-for-production-2026")
