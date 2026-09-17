from app.core.config import Settings


def test_bare_postgres_scheme_normalized_to_psycopg():
    s = Settings(database_url="postgres://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_bare_postgresql_scheme_normalized_to_psycopg():
    s = Settings(database_url="postgresql://user:pass@host:5432/db")
    assert s.database_url == "postgresql+psycopg://user:pass@host:5432/db"


def test_already_correct_scheme_left_untouched():
    url = "postgresql+psycopg://user:pass@host:5432/db"
    s = Settings(database_url=url)
    assert s.database_url == url


def test_default_cors_regex_covers_localhost_and_vercel():
    import re
    s = Settings()
    pattern = re.compile(s.cors_allow_origin_regex)
    assert pattern.fullmatch("http://localhost:3010")
    assert pattern.fullmatch("https://ril-o2c-platform.vercel.app")
    assert not pattern.fullmatch("https://evil.example.com")
