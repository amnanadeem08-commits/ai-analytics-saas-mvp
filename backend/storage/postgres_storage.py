"""
Future SaaS placeholder.

This MVP intentionally stores datasets as local CSV files and metadata as JSON.
When scaling to SaaS, this module can be replaced with SQLAlchemy repositories
for PostgreSQL without changing the API route layer.
"""


class PostgresStorageNotConfigured(RuntimeError):
    pass
