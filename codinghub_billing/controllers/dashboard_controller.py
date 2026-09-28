"""GUI-facing layer over dashboard_service — resolves the selected date
range and returns a fully-populated DashboardOverview for the view to render."""
from __future__ import annotations

from datetime import date

from database.connection import get_session
from services import dashboard_service
from services.dashboard_service import DashboardOverview


def get_overview(range_key: str, custom_from: date | None = None, custom_to: date | None = None) -> DashboardOverview:
    date_from, date_to = dashboard_service.resolve_range(range_key, custom_from, custom_to)
    with get_session() as session:
        return dashboard_service.get_overview(session, date_from, date_to)
