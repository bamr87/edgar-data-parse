# Generated manually for initial warehouse schema

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Company",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("cik", models.CharField(max_length=10, unique=True)),
                ("ticker", models.CharField(blank=True, max_length=10, null=True)),
                ("name", models.CharField(max_length=255)),
                ("industry", models.CharField(blank=True, max_length=255, null=True)),
                ("sic_code", models.CharField(blank=True, max_length=10, null=True)),
                ("sic_description", models.CharField(blank=True, max_length=255, null=True)),
                ("naics_code", models.CharField(blank=True, max_length=12, null=True)),
                ("hq_state", models.CharField(blank=True, max_length=2, null=True)),
                ("hq_country", models.CharField(blank=True, default="US", max_length=2)),
                ("management", models.JSONField(blank=True, default=dict)),
                ("headquarters", models.CharField(blank=True, max_length=255, null=True)),
                ("locations", models.JSONField(blank=True, default=list)),
                ("business_units", models.JSONField(blank=True, default=list)),
                ("product_types", models.JSONField(blank=True, default=list)),
                ("size", models.CharField(blank=True, max_length=255, null=True)),
                ("extra_attributes", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name="PeerGroup",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Filing",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accession_number", models.CharField(max_length=30)),
                ("form_type", models.CharField(max_length=20)),
                ("filing_date", models.DateField(blank=True, null=True)),
                ("period_of_report", models.DateField(blank=True, null=True)),
                ("url", models.URLField(blank=True, null=True)),
                ("local_path", models.CharField(blank=True, max_length=512, null=True)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="filings", to="warehouse.company")),
            ],
            options={"unique_together": {("company", "accession_number")}},
        ),
        migrations.CreateModel(
            name="Section",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("content", models.TextField()),
                ("filing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="sections", to="warehouse.filing")),
            ],
        ),
        migrations.CreateModel(
            name="Table",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("data", models.JSONField(default=list)),
                ("filing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="tables", to="warehouse.filing")),
            ],
        ),
        migrations.CreateModel(
            name="Fact",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("taxonomy", models.CharField(default="us-gaap", max_length=100)),
                ("concept", models.CharField(max_length=255)),
                ("period_start", models.DateField(blank=True, null=True)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("unit", models.CharField(blank=True, max_length=50, null=True)),
                ("value", models.DecimalField(blank=True, decimal_places=4, max_digits=20, null=True)),
                ("dimensions", models.JSONField(blank=True, default=dict)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="facts", to="warehouse.company")),
            ],
        ),
        migrations.CreateModel(
            name="DerivedMetric",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=64)),
                ("period_end", models.DateField(blank=True, null=True)),
                ("value", models.DecimalField(blank=True, decimal_places=6, max_digits=24, null=True)),
                ("unit", models.CharField(blank=True, max_length=32)),
                ("extra", models.JSONField(blank=True, default=dict)),
                ("computed_at", models.DateTimeField(auto_now_add=True)),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="derived_metrics", to="warehouse.company")),
            ],
        ),
        migrations.CreateModel(
            name="PeerGroupMember",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("company", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="peer_memberships", to="warehouse.company")),
                ("peer_group", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="memberships", to="warehouse.peergroup")),
            ],
        ),
        migrations.AddConstraint(
            model_name="peergroupmember",
            constraint=models.UniqueConstraint(fields=("peer_group", "company"), name="unique_peer_company"),
        ),
        migrations.AddIndex(
            model_name="fact",
            index=models.Index(fields=["company", "concept", "period_end"], name="warehouse_f_company_eb9fa8_idx"),
        ),
        migrations.AddIndex(
            model_name="derivedmetric",
            index=models.Index(fields=["company", "key", "period_end"], name="warehouse_d_company_7b2c0a_idx"),
        ),
    ]
