from django.db import models


class ListedIssuer(models.Model):
    """SEC company_tickers.json row cached in DB for search and resolution without live SEC reads."""

    cik = models.CharField(max_length=10, unique=True, db_index=True)
    ticker = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    name = models.CharField(max_length=255)
    synced_at = models.DateTimeField()

    class Meta:
        ordering = ["name"]
        indexes = [
            models.Index(fields=["name"]),
        ]

    def __str__(self) -> str:
        return f"{self.ticker or self.cik} — {self.name[:40]}"


class Company(models.Model):
    cik = models.CharField(max_length=10, unique=True)
    ticker = models.CharField(max_length=10, null=True, blank=True)
    name = models.CharField(max_length=255)
    industry = models.CharField(max_length=255, null=True, blank=True)
    sic_code = models.CharField(max_length=10, null=True, blank=True)
    sic_description = models.CharField(max_length=255, null=True, blank=True)
    naics_code = models.CharField(max_length=12, null=True, blank=True)
    hq_state = models.CharField(max_length=2, null=True, blank=True)
    hq_country = models.CharField(max_length=2, default="US", blank=True)
    hq_city = models.CharField(max_length=255, null=True, blank=True)
    management = models.JSONField(default=dict, blank=True)
    headquarters = models.CharField(max_length=255, null=True, blank=True)
    locations = models.JSONField(default=list, blank=True)
    business_units = models.JSONField(default=list, blank=True)
    product_types = models.JSONField(default=list, blank=True)
    size = models.CharField(max_length=255, null=True, blank=True)
    extra_attributes = models.JSONField(default=dict, blank=True)
    # CRM import (companies-clean.json / QAD-style customer export)
    crm_external_key = models.CharField(
        max_length=64, null=True, blank=True, unique=True, db_index=True
    )
    customer_class = models.CharField(max_length=64, null=True, blank=True)
    customer_type = models.CharField(max_length=64, null=True, blank=True)
    customer_vertical = models.CharField(max_length=128, null=True, blank=True)
    contract_status = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.ticker or self.cik} - {self.name}"


class EdgarSecPayload(models.Model):
    """Cached raw SEC JSON (submissions / companyfacts) for DB-first reads before live data.sec.gov calls."""

    class Kind(models.TextChoices):
        SUBMISSIONS = "submissions", "Submissions"
        COMPANY_FACTS = "company_facts", "Company facts"

    cik = models.CharField(max_length=10, db_index=True)
    kind = models.CharField(max_length=32, choices=Kind.choices)
    payload = models.JSONField()
    fetched_at = models.DateTimeField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["cik", "kind"], name="warehouse_edgar_sec_payload_cik_kind_uniq"),
        ]
        indexes = [
            models.Index(fields=["kind", "cik"]),
        ]

    def __str__(self) -> str:
        return f"{self.kind} CIK {self.cik}"


class EdgarEntitySyncState(models.Model):
    """Last successful EDGAR API sync timestamps per warehouse company."""

    company = models.OneToOneField(
        Company, on_delete=models.CASCADE, related_name="edgar_sync"
    )
    submissions_synced_at = models.DateTimeField(null=True, blank=True)
    facts_synced_at = models.DateTimeField(null=True, blank=True)
    last_error = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"EdgarSync<{self.company_id}>"


class CrmCompanyRecord(models.Model):
    """Staging row from CRM JSON (e.g. companies-clean.json); SEC CIK filled after title match."""

    key = models.CharField(max_length=64, unique=True, db_index=True)
    internal_object_id = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=512)
    end_user_number = models.CharField(max_length=32, null=True, blank=True)
    area = models.CharField(max_length=64, null=True, blank=True)
    country = models.CharField(max_length=64, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    customer_class = models.CharField(max_length=64, null=True, blank=True)
    customer_type = models.CharField(max_length=64, null=True, blank=True)
    global_hq_name = models.CharField(max_length=512, null=True, blank=True)
    parent_code = models.CharField(max_length=128, null=True, blank=True)
    contract_name = models.CharField(max_length=512, null=True, blank=True)
    contract_status = models.CharField(max_length=128, null=True, blank=True)
    vertical = models.CharField(max_length=128, null=True, blank=True)
    display = models.CharField(max_length=512, null=True, blank=True)
    import_label = models.CharField(max_length=128, null=True, blank=True)
    unique_name = models.CharField(max_length=512, null=True, blank=True)
    site_type = models.CharField(max_length=64, null=True, blank=True)
    account_id = models.CharField(max_length=64, null=True, blank=True)
    language = models.CharField(max_length=16, null=True, blank=True)
    created_source = models.DateTimeField(null=True, blank=True)
    updated_source = models.DateTimeField(null=True, blank=True)
    has_contract = models.BooleanField(null=True, blank=True)
    extra = models.JSONField(default=dict, blank=True)
    sec_cik = models.CharField(max_length=10, null=True, blank=True, db_index=True)
    sec_ticker = models.CharField(max_length=16, null=True, blank=True)
    match_status = models.CharField(max_length=32, null=True, blank=True)
    match_note = models.CharField(max_length=255, null=True, blank=True)
    matched_company = models.ForeignKey(
        Company,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="crm_sources",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["key"]

    def __str__(self):
        return f"{self.key} — {self.name[:60]}"


class PeerGroup(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name


class PeerGroupMember(models.Model):
    peer_group = models.ForeignKey(
        PeerGroup, on_delete=models.CASCADE, related_name="memberships"
    )
    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="peer_memberships"
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["peer_group", "company"], name="unique_peer_company"
            ),
        ]


class Filing(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="filings")
    accession_number = models.CharField(max_length=30)
    form_type = models.CharField(max_length=20)
    filing_date = models.DateField(null=True, blank=True)
    period_of_report = models.DateField(null=True, blank=True)
    url = models.URLField(null=True, blank=True)
    local_path = models.CharField(max_length=512, null=True, blank=True)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        unique_together = ("company", "accession_number")


class Section(models.Model):
    filing = models.ForeignKey(Filing, on_delete=models.CASCADE, related_name="sections")
    name = models.CharField(max_length=255)
    content = models.TextField()


class Table(models.Model):
    filing = models.ForeignKey(Filing, on_delete=models.CASCADE, related_name="tables")
    data = models.JSONField(default=list)


class Fact(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="facts")
    taxonomy = models.CharField(max_length=100, default="us-gaap")
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


class DerivedMetric(models.Model):
    """Computed KPIs / ratios."""

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="derived_metrics"
    )
    key = models.CharField(max_length=64)
    period_end = models.DateField(null=True, blank=True)
    value = models.DecimalField(max_digits=24, decimal_places=6, null=True, blank=True)
    unit = models.CharField(max_length=32, blank=True)
    extra = models.JSONField(default=dict, blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "key", "period_end"]),
        ]
