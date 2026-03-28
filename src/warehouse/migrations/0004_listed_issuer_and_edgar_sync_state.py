import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("warehouse", "0003_crm_company_and_company_metadata"),
    ]

    operations = [
        migrations.CreateModel(
            name="ListedIssuer",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("cik", models.CharField(db_index=True, max_length=10, unique=True)),
                (
                    "ticker",
                    models.CharField(blank=True, db_index=True, max_length=10, null=True),
                ),
                ("name", models.CharField(max_length=255)),
                ("synced_at", models.DateTimeField()),
            ],
            options={
                "ordering": ["name"],
            },
        ),
        migrations.AddIndex(
            model_name="listedissuer",
            index=models.Index(fields=["name"], name="warehouse_l_name_7f3a8b_idx"),
        ),
        migrations.CreateModel(
            name="EdgarEntitySyncState",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("submissions_synced_at", models.DateTimeField(blank=True, null=True)),
                ("facts_synced_at", models.DateTimeField(blank=True, null=True)),
                ("last_error", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "company",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="edgar_sync",
                        to="warehouse.company",
                    ),
                ),
            ],
        ),
    ]
