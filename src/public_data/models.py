from django.db import models


class ExternalSeries(models.Model):
    """Registered public time series (e.g. FRED id)."""

    PROVIDER_CHOICES = [
        ("fred", "FRED"),
        ("manual", "Manual"),
    ]

    provider = models.CharField(max_length=32, choices=PROVIDER_CHOICES)
    external_id = models.CharField(max_length=64)
    title = models.CharField(max_length=512, blank=True)
    frequency = models.CharField(max_length=32, blank=True)
    units = models.CharField(max_length=128, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["provider", "external_id"],
                name="unique_provider_series",
            ),
        ]

    def __str__(self):
        return f"{self.provider}:{self.external_id}"


class SeriesObservation(models.Model):
    series = models.ForeignKey(
        ExternalSeries, on_delete=models.CASCADE, related_name="observations"
    )
    observation_date = models.DateField(db_index=True)
    value = models.DecimalField(max_digits=24, decimal_places=6)
    source_url = models.URLField(max_length=1024, blank=True)
    retrieved_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["series", "observation_date"],
                name="unique_series_date",
            ),
        ]
        indexes = [
            models.Index(fields=["series", "observation_date"]),
        ]


class SeriesBundle(models.Model):
    """Named pack of series (e.g. macro FRED bundle)."""

    slug = models.SlugField(unique=True, max_length=64)
    name = models.CharField(max_length=128)
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class SeriesBundleItem(models.Model):
    bundle = models.ForeignKey(
        SeriesBundle, on_delete=models.CASCADE, related_name="items"
    )
    series = models.ForeignKey(
        ExternalSeries, on_delete=models.CASCADE, related_name="bundle_items"
    )
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.UniqueConstraint(
                fields=["bundle", "series"], name="unique_bundle_series"
            ),
        ]
