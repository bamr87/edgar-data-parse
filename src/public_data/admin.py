from django.contrib import admin

from .models import ExternalSeries, SeriesBundle, SeriesBundleItem, SeriesObservation


class SeriesBundleItemInline(admin.TabularInline):
    model = SeriesBundleItem
    extra = 0


@admin.register(ExternalSeries)
class ExternalSeriesAdmin(admin.ModelAdmin):
    list_display = ("provider", "external_id", "title", "last_synced_at")
    search_fields = ("external_id", "title")


@admin.register(SeriesObservation)
class SeriesObservationAdmin(admin.ModelAdmin):
    list_display = ("series", "observation_date", "value")
    list_filter = ("series",)


@admin.register(SeriesBundle)
class SeriesBundleAdmin(admin.ModelAdmin):
    list_display = ("slug", "name")
    inlines = [SeriesBundleItemInline]
