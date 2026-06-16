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
    """Warehouse issuer: SEC CIK, optional ticker, CRM-enriched attributes, and JSON extras."""

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
    # CRM import (data/local/companies-clean.json — QAD-style customer export)
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
    """Staging row from CRM JSON (e.g. data/local/companies-clean.json); SEC CIK filled after title match."""

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


class FilingDocument(models.Model):
    """One ``<DOCUMENT>`` section of a full SEC submission (.txt), with extracted text.

    Mirrors OpenEDGAR's FilingDocument: a filing decomposes into ordered documents
    (primary doc + exhibits), each addressed by the SHA-1 of its raw content (stored
    in object storage) with extracted text kept in the DB for full-text search.
    """

    filing = models.ForeignKey(
        Filing, on_delete=models.CASCADE, related_name="documents"
    )
    type = models.CharField(max_length=255, null=True, blank=True, db_index=True)
    sequence = models.IntegerField(default=0, db_index=True)
    file_name = models.CharField(max_length=512, null=True, blank=True)
    content_type = models.CharField(max_length=128, null=True, blank=True)
    description = models.CharField(max_length=512, null=True, blank=True)
    sha1 = models.CharField(max_length=40, db_index=True)
    raw_key = models.CharField(max_length=128, null=True, blank=True)
    text = models.TextField(blank=True, default="")
    start_pos = models.IntegerField(default=0)
    end_pos = models.IntegerField(default=0)
    is_processed = models.BooleanField(default=False, db_index=True)
    is_error = models.BooleanField(default=False, db_index=True)

    class Meta:
        unique_together = ("filing", "sequence")
        ordering = ["filing_id", "sequence"]

    def __str__(self) -> str:
        return f"FilingDocument filing={self.filing_id} seq={self.sequence} type={self.type}"


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


# --- Company-360 unified layer (Phase 9) ---


class DataSource(models.Model):
    """Registry of sources that contribute data (SEC EDGAR, FRED, CRM, …)."""

    name = models.CharField(max_length=64, unique=True)
    kind = models.CharField(max_length=32, blank=True)  # filings | facts | macro | crm | enrichment
    base_url = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.name


class ExternalIdentifier(models.Model):
    """Cross-source identifier for a Company (CIK, ticker, CRM key, FRED id, …).

    Lets one canonical Company be joined across every source (entity resolution).
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="identifiers"
    )
    system = models.CharField(max_length=32, db_index=True)  # cik | ticker | crm | fred | ...
    value = models.CharField(max_length=128, db_index=True)
    confidence = models.FloatField(default=1.0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["system", "value"], name="external_identifier_uniq"),
        ]

    def __str__(self) -> str:
        return f"{self.system}={self.value} -> company {self.company_id}"


class ContentChunk(models.Model):
    """A retrievable text chunk with provenance and an optional embedding.

    AI-ready substrate for retrieval/RAG. ``embedding`` is a JSON list of floats,
    populated only when ``ENABLE_EMBEDDINGS`` is set (default off). For ANN at scale,
    the production upgrade path is a pgvector column on PostgreSQL.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="content_chunks", null=True, blank=True
    )
    filing_document = models.ForeignKey(
        "FilingDocument", on_delete=models.CASCADE, related_name="chunks", null=True, blank=True
    )
    source = models.CharField(max_length=64, db_index=True)  # provenance, e.g. 'filing_document'
    char_start = models.IntegerField(default=0)
    char_end = models.IntegerField(default=0)
    text = models.TextField()
    embedding = models.JSONField(null=True, blank=True)
    embedding_model = models.CharField(max_length=64, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["company", "source"]),
        ]

    def __str__(self) -> str:
        return f"ContentChunk company={self.company_id} [{self.char_start}:{self.char_end}]"


# --- Leadership & stakeholder analytics ---


class Person(models.Model):
    """A named individual extracted from SEC filings (officer/director/owner).

    Identity is anchored to the SEC reporting-owner CIK when available (the
    authoritative public identifier); otherwise to a normalized name. ``external``
    holds provenance-tagged enrichment from licensed/manual sources — never scraped.
    """

    full_name = models.CharField(max_length=255)
    normalized_name = models.CharField(max_length=255, db_index=True)
    cik = models.CharField(max_length=10, null=True, blank=True, unique=True, db_index=True)
    external = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name


class LeadershipPosition(models.Model):
    """A person's role at a company, derived from SEC ownership filings (Forms 3/4/5).

    ``first_seen``/``last_seen`` are filing-date bounds (a tenure *proxy*, not an
    official appointment record). ``net_insider_shares`` aggregates Form 4
    acquired(+)/disposed(-) activity — an alignment ("skin in the game") signal.
    """

    person = models.ForeignKey(Person, on_delete=models.CASCADE, related_name="positions")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="leadership")
    title = models.CharField(max_length=255, blank=True)
    is_director = models.BooleanField(default=False)
    is_officer = models.BooleanField(default=False)
    is_ten_percent_owner = models.BooleanField(default=False)
    first_seen = models.DateField(null=True, blank=True)
    last_seen = models.DateField(null=True, blank=True, db_index=True)
    filings_count = models.IntegerField(default=0)
    net_insider_shares = models.DecimalField(
        max_digits=24, decimal_places=2, default=0
    )
    source = models.CharField(max_length=64, default="sec_form345")
    source_url = models.CharField(max_length=512, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["person", "company"], name="leadership_person_company_uniq"
            ),
        ]
        ordering = ["-last_seen"]

    def __str__(self) -> str:
        return f"{self.person.full_name} — {self.title or 'insider'} @ company {self.company_id}"


class StakeholderAssessment(models.Model):
    """Transparent, source-cited 'stakeholder orientation' analysis for a company/period.

    A HEURISTIC model over public XBRL facts — signals about capital allocation
    (reinvestment vs. shareholder payout, local-investment proxy, R&D, insider
    alignment), NOT a personal approval rating, character judgment, or endorsement,
    and NOT investment/HR advice. ``orientation_index`` runs roughly -1 (payout /
    shareholder-tilted) to +1 (reinvestment / stakeholder-tilted); every input is
    disclosed in ``signals`` with its source concept and period.
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="stakeholder_assessments"
    )
    period_start = models.DateField(null=True, blank=True)
    period_end = models.DateField(null=True, blank=True, db_index=True)
    orientation_index = models.FloatField(null=True, blank=True)
    label = models.CharField(max_length=64, blank=True)
    signals = models.JSONField(default=list, blank=True)
    method_version = models.CharField(max_length=16, default="1.0")
    caveats = models.TextField(blank=True)
    computed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["company", "period_end", "method_version"],
                name="stakeholder_assessment_uniq",
            ),
        ]
        ordering = ["-period_end"]

    def __str__(self) -> str:
        return f"StakeholderAssessment company={self.company_id} {self.period_end} idx={self.orientation_index}"


class LeadershipAnalysis(models.Model):
    """LLM-generated narrative analysis of leadership, STRICTLY grounded in SEC text.

    Optional and gated (``ENABLE_AI_ANALYSIS``, off by default). The model extracts
    leadership initiatives, verbatim quotes, and stated forward direction *only* from
    provided SEC filing excerpts, each citing its source passage. It NEVER invents
    quotes and makes NO personal/character/'approval' judgments about any individual —
    that boundary is enforced in the system prompt and documented in
    ``docs/leadership-methodology.md``. Distinct from the heuristic
    ``StakeholderAssessment`` (computed from XBRL facts, no LLM).
    """

    company = models.ForeignKey(
        Company, on_delete=models.CASCADE, related_name="leadership_analyses"
    )
    enabled = models.BooleanField(default=False)  # False = analyzer was off / no-op
    summary = models.TextField(blank=True)
    initiatives = models.JSONField(default=list, blank=True)  # [{title, description, source}]
    quotes = models.JSONField(default=list, blank=True)       # [{text, speaker, source}]
    direction = models.TextField(blank=True)
    used_sources = models.JSONField(default=list, blank=True)  # [{tag, accession, type}]
    backend = models.CharField(max_length=32, blank=True)
    model_name = models.CharField(max_length=64, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["company", "-created_at"])]

    def __str__(self) -> str:
        return f"LeadershipAnalysis company={self.company_id} backend={self.backend} @ {self.created_at}"
