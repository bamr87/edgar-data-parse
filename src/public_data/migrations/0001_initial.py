import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="ExternalSeries",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("provider", models.CharField(choices=[("fred", "FRED"), ("manual", "Manual")], max_length=32)),
                ("external_id", models.CharField(max_length=64)),
                ("title", models.CharField(blank=True, max_length=512)),
                ("frequency", models.CharField(blank=True, max_length=32)),
                ("units", models.CharField(blank=True, max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("last_synced_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="SeriesBundle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("slug", models.SlugField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=128)),
                ("description", models.TextField(blank=True)),
            ],
        ),
        migrations.CreateModel(
            name="SeriesObservation",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("observation_date", models.DateField(db_index=True)),
                ("value", models.DecimalField(decimal_places=6, max_digits=24)),
                ("source_url", models.URLField(blank=True, max_length=1024)),
                ("retrieved_at", models.DateTimeField(auto_now_add=True)),
                ("series", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="observations", to="public_data.externalseries")),
            ],
        ),
        migrations.CreateModel(
            name="SeriesBundleItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("sort_order", models.PositiveIntegerField(default=0)),
                ("bundle", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="public_data.seriesbundle")),
                ("series", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bundle_items", to="public_data.externalseries")),
            ],
            options={"ordering": ["sort_order", "id"]},
        ),
        migrations.AddConstraint(
            model_name="externalseries",
            constraint=models.UniqueConstraint(fields=("provider", "external_id"), name="unique_provider_series"),
        ),
        migrations.AddConstraint(
            model_name="seriesobservation",
            constraint=models.UniqueConstraint(fields=("series", "observation_date"), name="unique_series_date"),
        ),
        migrations.AddIndex(
            model_name="seriesobservation",
            index=models.Index(fields=["series", "observation_date"], name="public_data_series_i_7a1b2c_idx"),
        ),
        migrations.AddConstraint(
            model_name="seriesbundleitem",
            constraint=models.UniqueConstraint(fields=("bundle", "series"), name="unique_bundle_series"),
        ),
    ]
