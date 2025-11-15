from django.db import models


class Company(models.Model):
    cik = models.CharField(max_length=10, unique=True)
    ticker = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255, null=True, blank=True)
    management = models.JSONField(default=dict, blank=True)
    headquarters = models.CharField(max_length=255, null=True, blank=True)
    locations = models.JSONField(default=list, blank=True)
    business_units = models.JSONField(default=list, blank=True)
    product_types = models.JSONField(default=list, blank=True)
    size = models.CharField(max_length=255, null=True, blank=True)
    extra_attributes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticker or self.cik} - {self.name}"


class Filing(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='filings')
    accession_number = models.CharField(max_length=30)
    form_type = models.CharField(max_length=20)
    filing_date = models.DateField(null=True, blank=True)
    period_of_report = models.DateField(null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    local_path = models.CharField(max_length=512, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ('company', 'accession_number')


class Section(models.Model):
    filing = models.ForeignKey(Filing, on_delete=models.CASCADE, related_name='sections')
    name = models.CharField(max_length=255)
    content = models.TextField()


class Table(models.Model):
    filing = models.ForeignKey(Filing, on_delete=models.CASCADE, related_name='tables')
    data = models.JSONField(default=list)  # store rows/columns as parsed


class Fact(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='facts')
    taxonomy = models.CharField(max_length=100, default='us-gaap')
    concept = models.CharField(max_length=255)
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True)
    unit = models.CharField(max_length=50, null=True, blank=True)
    value = models.DecimalField(max_digits=20, decimal_places=4, null=True, blank=True)
    dimensions = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "concept", "period_end"]),
        ]
