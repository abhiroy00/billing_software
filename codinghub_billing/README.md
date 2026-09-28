# CodingHub Billing & Business Management Software

Desktop billing/ERP application for CodingHub, built with Python, CustomTkinter/ttk, and
SQLAlchemy over SQLite.

## Status: Phase 1 — Foundation

This phase implements: project architecture, full database schema, the design system, the
reusable component library, authentication + RBAC groundwork, the first-run Setup Wizard, the
main application shell, and a fully DB-backed Dashboard.

Customers, Courses, Billing/Invoicing, Payments, Expenses, Reports, Users,
Settings, Backup/Restore and Audit Log viewing are implemented.

## Setup

```
pip install -r requirements.txt
python app.py
```

On first launch you'll be guided through a 5-step Setup Wizard (business info, admin account,
invoice settings, backup folder, finish) before reaching the Login screen.

Application data (SQLite database, backups, invoices, exports, logs, config) lives outside this
folder, under `%LOCALAPPDATA%\CodingHub` on Windows (override with the `CODINGHUB_APP_DATA_DIR`
environment variable, e.g. for tests).

## Tests

```
python -m pytest tests/ -q
```

## Architecture

```
GUI (gui/)  ->  Controllers (controllers/)  ->  Services (services/)  ->  Repositories (database/repositories/)  ->  SQLAlchemy models (database/models/)  ->  SQLite
```

Every color/font/spacing value comes from `gui/theme.py`. Every path/constant comes from
`config.py`. GUI code never opens a DB session or writes SQL directly — it always goes through a
controller function.
