"""Postgres-only GIN index for FilingDocument full-text search.

No-op on other backends (SQLite dev/test) so migrations stay cross-database.
"""

from django.db import migrations

_INDEX = "warehouse_filingdocument_text_fts"
_TABLE = "warehouse_filingdocument"


def add_gin(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(
        f"CREATE INDEX IF NOT EXISTS {_INDEX} "
        f"ON {_TABLE} USING gin (to_tsvector('english', text));"
    )


def drop_gin(apps, schema_editor):
    if schema_editor.connection.vendor != "postgresql":
        return
    schema_editor.execute(f"DROP INDEX IF EXISTS {_INDEX};")


class Migration(migrations.Migration):
    dependencies = [("warehouse", "0007_filingdocument")]
    operations = [migrations.RunPython(add_gin, drop_gin)]
