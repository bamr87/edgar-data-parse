"""Rate-limited, resumable bulk sync of EDGAR datasets across all warehouse companies.

For each company, pulls and caches the selected datasets from SEC EDGAR — submissions
(filings), XBRL facts, derived metrics, leadership (Forms 3/4/5), and the stakeholder
index — pacing requests to respect SEC fair-access (10 req/s max; declared User-Agent).

Resumable: skips companies already synced (via ``EdgarEntitySyncState`` timestamps)
unless ``--force``. Safe to Ctrl-C and rerun — it picks up where it left off. Failures
on one company are recorded and skipped, never aborting the whole run.

Examples:
    python manage.py sync_all_companies --datasets submissions,facts,metrics --delay 0.3
    python manage.py sync_all_companies --limit 200 --with-ticker-only
    python manage.py sync_all_companies --datasets all --force
"""

from __future__ import annotations

import time

from django.core.management.base import BaseCommand
from django.utils import timezone

from sec_edgar.exceptions import EdgarRateLimitError
from warehouse.models import Company, EdgarEntitySyncState

ALL_DATASETS = ["submissions", "facts", "metrics", "leadership", "stakeholder"]
RATE_LIMIT_SLEEP = 65  # seconds to back off on a 429 before one retry


class Command(BaseCommand):
    help = "Rate-limited, resumable bulk sync of EDGAR datasets for every company."

    def add_arguments(self, parser):
        parser.add_argument(
            "--datasets",
            default="submissions,facts,metrics",
            help=f"Comma list of {ALL_DATASETS} (or 'all'). Default: submissions,facts,metrics.",
        )
        parser.add_argument("--delay", type=float, default=0.3, help="Seconds between SEC requests (>=0.1 keeps well under 10/s).")
        parser.add_argument("--limit", type=int, default=0, help="Max companies to process (0 = all).")
        parser.add_argument("--offset", type=int, default=0, help="Skip the first N companies (for sharding).")
        parser.add_argument("--with-ticker-only", action="store_true", help="Only companies that have a ticker (skip shells/funds).")
        parser.add_argument("--leadership-limit", type=int, default=15, help="Max ownership filings per company for leadership extraction.")
        parser.add_argument("--force", action="store_true", help="Re-sync even if already synced.")
        parser.add_argument("--user-agent-email", default=None, help="Override SEC User-Agent contact email.")

    def handle(self, *args, **options):
        from warehouse.services.edgar.metrics import compute_derived_metrics
        from warehouse.services.edgar.sync import EdgarSyncService

        datasets = self._parse_datasets(options["datasets"])
        delay = max(0.1, options["delay"])
        force = options["force"]
        ua = options["user_agent_email"]
        lead_limit = options["leadership_limit"]

        qs = Company.objects.all().order_by("id")
        if options["with_ticker_only"]:
            qs = qs.exclude(ticker__isnull=True).exclude(ticker="")
        if options["offset"]:
            qs = qs[options["offset"]:]
        if options["limit"]:
            qs = qs[: options["limit"]]

        total = qs.count()
        self.stdout.write(
            f"Syncing {datasets} for {total} companies "
            f"(delay={delay}s, force={force}). Resumable — Ctrl-C and rerun is safe."
        )

        done = ok = failed = skipped = 0
        for company in qs.iterator(chunk_size=200):
            done += 1
            state, _ = EdgarEntitySyncState.objects.get_or_create(company=company)
            try:
                touched = self._sync_one(
                    company, state, datasets, delay, force, ua, lead_limit,
                    EdgarSyncService, compute_derived_metrics,
                )
                if touched:
                    ok += 1
                else:
                    skipped += 1
            except EdgarRateLimitError:
                # Honor SEC fair-access: back off hard, then retry this company once.
                self.stdout.write(self.style.WARNING(f"  rate-limited at {company.cik}; sleeping {RATE_LIMIT_SLEEP}s"))
                time.sleep(RATE_LIMIT_SLEEP)
                try:
                    self._sync_one(company, state, datasets, delay, force, ua, lead_limit, EdgarSyncService, compute_derived_metrics)
                    ok += 1
                except Exception as e:  # noqa: BLE001
                    failed += 1
                    self._record_error(state, e)
            except Exception as e:  # noqa: BLE001 - never abort the whole run for one company
                failed += 1
                self._record_error(state, e)

            if done % 25 == 0 or done == total:
                self.stdout.write(f"  [{done}/{total}] ok={ok} skipped={skipped} failed={failed}")

        self.stdout.write(self.style.SUCCESS(f"Done. processed={done} synced={ok} skipped={skipped} failed={failed}"))

    # ---- helpers ----
    def _parse_datasets(self, raw: str) -> list[str]:
        if raw.strip().lower() == "all":
            return ALL_DATASETS
        picked = [d.strip() for d in raw.split(",") if d.strip()]
        bad = [d for d in picked if d not in ALL_DATASETS]
        if bad:
            from django.core.management.base import CommandError

            raise CommandError(f"Unknown dataset(s) {bad}; choose from {ALL_DATASETS} or 'all'.")
        return picked

    def _sync_one(self, company, state, datasets, delay, force, ua, lead_limit, Sync, compute_metrics) -> bool:
        """Sync the requested datasets for one company. Returns True if anything ran."""
        touched = False

        if "submissions" in datasets and (force or state.submissions_synced_at is None):
            Sync.sync_submissions(company, user_agent_email=ua)
            state.submissions_synced_at = timezone.now()
            state.save(update_fields=["submissions_synced_at", "updated_at"])
            touched = True
            time.sleep(delay)

        if "facts" in datasets and (force or state.facts_synced_at is None):
            Sync.sync_facts(company, user_agent_email=ua)
            state.facts_synced_at = timezone.now()
            state.last_error = ""
            state.save(update_fields=["facts_synced_at", "last_error", "updated_at"])
            touched = True
            time.sleep(delay)

        if "metrics" in datasets and touched:  # local compute; only if facts may have changed
            compute_metrics(company)

        if "leadership" in datasets:
            from warehouse.services.leadership import sync_leadership

            sync_leadership(company, user_agent_email=ua, limit=lead_limit)
            touched = True
            time.sleep(delay)

        if "stakeholder" in datasets:
            from warehouse.services.stakeholder import compute_stakeholder_assessment

            compute_stakeholder_assessment(company)  # local compute over cached facts

        return touched

    def _record_error(self, state, err: Exception) -> None:
        state.last_error = str(err)[:1000]
        state.save(update_fields=["last_error", "updated_at"])
        self.stdout.write(self.style.WARNING(f"  failed {state.company.cik}: {str(err)[:120]}"))
