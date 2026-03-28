from django.contrib import admin

from .models import (
    Company,
    CrmCompanyRecord,
    DerivedMetric,
    EdgarEntitySyncState,
    EdgarSecPayload,
    Fact,
    Filing,
    ListedIssuer,
    PeerGroup,
    Section,
    Table,
)


@admin.register(ListedIssuer)
class ListedIssuerAdmin(admin.ModelAdmin):
    list_display = ("cik", "ticker", "name", "synced_at")
    search_fields = ("cik", "ticker", "name")


@admin.register(EdgarSecPayload)
class EdgarSecPayloadAdmin(admin.ModelAdmin):
    list_display = ("cik", "kind", "fetched_at", "updated_at")
    list_filter = ("kind",)
    search_fields = ("cik",)
    readonly_fields = ("payload", "fetched_at", "updated_at")


@admin.register(EdgarEntitySyncState)
class EdgarEntitySyncStateAdmin(admin.ModelAdmin):
    list_display = ("company", "submissions_synced_at", "facts_synced_at", "updated_at")
    raw_id_fields = ("company",)


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "ticker",
        "cik",
        "industry",
        "sic_code",
        "hq_state",
        "crm_external_key",
        "customer_vertical",
    )
    search_fields = ("name", "ticker", "cik", "crm_external_key")


@admin.register(CrmCompanyRecord)
class CrmCompanyRecordAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "sec_cik", "match_status", "matched_company")
    list_filter = ("match_status",)
    search_fields = ("key", "name", "unique_name", "sec_cik")
    raw_id_fields = ("matched_company",)


@admin.register(Filing)
class FilingAdmin(admin.ModelAdmin):
    list_display = ("company", "form_type", "filing_date", "accession_number")
    search_fields = ("accession_number",)
    list_filter = ("form_type",)


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ("filing", "name")
    search_fields = ("name",)


@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ("filing",)


@admin.register(Fact)
class FactAdmin(admin.ModelAdmin):
    list_display = ("company", "concept", "period_end", "value")
    search_fields = ("concept",)
    list_filter = ("taxonomy",)


@admin.register(DerivedMetric)
class DerivedMetricAdmin(admin.ModelAdmin):
    list_display = ("company", "key", "period_end", "value")
    search_fields = ("key",)


@admin.register(PeerGroup)
class PeerGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "created_at")
    search_fields = ("name",)
