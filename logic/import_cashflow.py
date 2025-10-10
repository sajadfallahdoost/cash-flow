# apps/imports/management/commands/import_cashflow.py
import pathlib, decimal
import pandas as pd
from django.core.management.base import BaseCommand
from persiantools.jdatetime import JalaliDate
from django.db import transaction as db_tx

from core.models import Holding, Company, Project
from transactions.models import Transaction, Category
from milestones.models import Milestone
from imports.models import SpreadsheetImport
from commons.choices import TransactionType, MilestoneStatus, ImportStatus

INFLOW_CAT, _ = Category.objects.get_or_create(
    name="CF_INFLOW", defaults=dict(t_type=TransactionType.INFLOW)
)
OUTFLOW_CAT, _ = Category.objects.get_or_create(
    name="CF_OUTFLOW", defaults=dict(t_type=TransactionType.OUTFLOW)
)
OPEN_BAL_CAT, _ = Category.objects.get_or_create(
    name="OPENING_BALANCE", defaults=dict(t_type=TransactionType.INFLOW)
)


class Command(BaseCommand):
    """Parse the 'Cash Flow' sheet of the provided XLSX."""

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=pathlib.Path)
        parser.add_argument("--user-id", type=int, required=True)

    @db_tx.atomic
    def handle(self, *args, **opts):
        path = opts["xlsx_path"]
        uploader_id = opts["user_id"]

        # Hold-company-project bootstrap
        holding, _ = Holding.objects.get_or_create(name="ایده تدبیر مهام")
        company, _ = Company.objects.get_or_create(
            name="ایده تدبیر مهام", defaults=dict(holding=holding, base_currency="IRR")
        )
        project, _ = Project.objects.get_or_create(
            company=company, code="TEST", defaults=dict(name="Test Project")
        )

        # Import header
        imp = SpreadsheetImport.objects.create(
            filename=path.name,
            uploaded_by_id=uploader_id,
            status=ImportStatus.PROCESSING,
        )

        df = pd.read_excel(path, sheet_name="Cash Flow", engine="openpyxl")
        df = df.fillna("")

        # Expect headers in row 0 (month names) and row 1 (10/20/30)
        months = [cell for cell in df.columns[1:]]          # Jalali month strings
        periods = [(m, day) for m in months for day in (10, 20, 30)]

        rows_to_insert = []
        for idx, row in df.iterrows():
            label = str(row.iloc[0]).strip()
            if label == "":                # skip blank
                continue
            if "ورودی" in label:
                cat = INFLOW_CAT
                t_type = TransactionType.INFLOW
            elif "خروجی" in label:
                cat = OUTFLOW_CAT
                t_type = TransactionType.OUTFLOW
            elif "مانده اول دوره" in label:
                cat = OPEN_BAL_CAT
                t_type = TransactionType.INFLOW
            else:
                continue   # ignore any totals / unknown rows

            for col_i, (month_fa, day) in enumerate(periods, start=1):
                val = row.iloc[col_i]
                if pd.isna(val) or str(val).strip() == "":
                    continue
                amount = decimal.Decimal(str(val).replace(",", ""))

                # Convert month/day (Persian) → Gregorian date
                year_fa = 1404 if "۱۴۰۴" in month_fa else 1403  # crude example
                month_num = JalaliDate.MONTHS_FA.index(month_fa.split()[0]) + 1
                g_date = JalaliDate(year_fa, month_num, day).to_gregorian()

                milestone, _ = Milestone.objects.get_or_create(
                    project=project,
                    name=month_fa,
                    defaults=dict(
                        due_date=g_date.replace(day=28),  # end-of-month approx
                        planned_amt=0,
                        status=MilestoneStatus.PLANNED,
                    ),
                )

                rows_to_insert.append(
                    Transaction(
                        company=company,
                        project=project,
                        category=cat,
                        milestone=milestone,
                        import_ref=imp,
                        txn_date=g_date,
                        amount=amount,
                        currency="IRR",
                    )
                )

        # Bulk insert
        Transaction.objects.bulk_create(rows_to_insert)

        imp.status = ImportStatus.COMPLETED
        imp.project = project          # optional
        imp.save(update_fields=["status", "project"])

        self.stdout.write(
            self.style.SUCCESS(f"Imported {len(rows_to_insert)} cash-flow rows from {path}")
        )
