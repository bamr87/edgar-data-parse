from django.contrib import admin

from .models import Company, Fact, Filing, Section, Table


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "ticker", "cik", "industry")
    search_fields = ("name", "ticker", "cik")


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
    search_fields = ("concept",)
    list_filter = ("taxonomy",)
