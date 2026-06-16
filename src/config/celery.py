"""Celery application for background SEC/processing jobs.

Configured from Django settings under the ``CELERY_`` namespace (see
``config.settings``). Tasks are autodiscovered from each app's ``tasks.py``.
In tests, ``CELERY_TASK_ALWAYS_EAGER`` runs tasks inline with no broker.
"""

from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

app = Celery("edgar")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
