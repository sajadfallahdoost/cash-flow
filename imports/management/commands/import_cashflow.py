import pathlib, decimal, re
from datetime import date

import pandas as pd
from tqdm import tqdm  # ← progress bar

from django.core.management.base import BaseCommand
from django.db import transaction as db_tx
from persiantools.jdatetime import JalaliDate

from core.models import Holding, Company, Project
from milestones.models import Milestone
from transactions.models import Transaction, Category
from imports.models import SpreadsheetImport
from commons.choices import MilestoneStatus, ImportStatus, TransactionType

# ──────────────────────────────────────────────────────────────────────────────
PERSIAN_MONTHS = {
    "فروردین": 1, "اردیبهشت": 2, "خرداد": 3,
    "تیر": 4, "مرداد": 5, "شهریور": 6,
    "مهر": 7, "آبان": 8, "آذر": 9,
    "دی": 10, "بهمن": 11, "اسفند": 12,
}
DEHE_MAP = {"10": "دهه اول", "20": "دهه دوم", "30": "دهه سوم"}
YEAR_RX = re.compile(r"(13|14)\d{2}")
MONTH_RX = re.compile("|".join(PERSIAN_MONTHS.keys()))
CANDIDATE_LABEL_COLS = (3, 2, 1)
# ──────────────────────────────────────────────────────────────────────────────


class Command(BaseCommand):
    help = "Import 'Cash Flow' → build Milestones, Categories & Transactions"

    def add_arguments(self, parser):
        parser.add_argument("xlsx_path", type=pathlib.Path)
        parser.add_argument("--user-id", type=int, required=True)

    def find_label(self, df, row_idx) -> str | None:
        for col in CANDIDATE_LABEL_COLS:
            val = str(df.iat[row_idx, col]).strip()
            if val and "مجموع" not in val:
                return val
        return None

    def infer_transaction_type(self, code_str: str, label: str) -> str:
        if code_str.startswith("3"):
            return TransactionType.OUTFLOW
        if code_str.startswith("2"):
            return TransactionType.INFLOW
        if any(x in label for x in ("هزینه", "حقوق", "سربار", "پرداخت")):
            return TransactionType.OUTFLOW
        return TransactionType.INFLOW

    @db_tx.atomic
    def handle(self, *_, **opts):
        path = opts["xlsx_path"]
        uploader_id = opts["user_id"]

        # ── Setup project/holding ──────────────────────────────────────────
        holding, _ = Holding.objects.get_or_create(name="ایده تدبیر مهام")
        company, _ = Company.objects.get_or_create(
            name="ایده تدبیر مهام",
            defaults=dict(holding=holding, base_currency="IRR"),
        )
        project, _ = Project.objects.get_or_create(
            company=company,
            code="TEST",
            defaults=dict(
                name="Test Project",
                start_date=date.today(),
                status="Active",
            ),
        )
        imp = SpreadsheetImport.objects.create(
            filename=path.name,
            uploaded_by_id=uploader_id,
            status=ImportStatus.PROCESSING,
        )

        # ── Load sheet & headers ───────────────────────────────────────────
        df = pd.read_excel(path, sheet_name="Cash Flow", engine="openpyxl", header=None)
        df.fillna("", inplace=True)

        months_hdr = df.loc[1, 5:].tolist()
        days_hdr = df.loc[2, 5:].tolist()

        # forward-fill month names
        last = ""
        for i, m in enumerate(months_hdr):
            m = str(m).strip()
            if m:
                last = m
            months_hdr[i] = last

        periods = list(zip(months_hdr, days_hdr))
        to_create = []

        # ── Parse data rows with tqdm ───────────────────────────────────────
        for r in tqdm(range(4, len(df)), desc="📄 Reading rows", unit="row"):
            label = self.find_label(df, r)
            if not label:
                continue

            code_str = str(df.iat[r, 0]).strip()
            t_type = self.infer_transaction_type(code_str, label)

            cat, _ = Category.objects.get_or_create(
                name=label,
                defaults=dict(t_type=t_type, is_active=True, sort_order=0),
            )

            # ── Iterate through دهه columns with tqdm ──────────────────────
            for c, (m_hdr, d_hdr) in tqdm(
                list(enumerate(periods, start=5)),
                desc=f"🔢 Columns for '{label}'",
                unit="cell",
                leave=False,
            ):
                cell = df.iat[r, c]
                if pd.isna(cell) or str(cell).strip() == "":
                    continue

                try:
                    amt = decimal.Decimal(str(cell).replace(",", "").strip())
                except decimal.InvalidOperation:
                    continue

                ym = YEAR_RX.search(str(m_hdr))
                year_fa = int(ym.group()) if ym else 1404

                mm = MONTH_RX.search(str(m_hdr))
                if not mm:
                    self.stdout.write(f"⚠️ skip month in header '{m_hdr}'")
                    continue

                month_name = mm.group()
                month_num = PERSIAN_MONTHS[month_name]

                dc = str(d_hdr).strip().replace(".0", "")
                dehe = DEHE_MAP.get(dc)
                if not dehe:
                    continue

                ms_name = f"{dehe} {month_name} {year_fa}"
                due = JalaliDate(year_fa, month_num, 1).to_gregorian().replace(day=28)

                ms, created = Milestone.objects.get_or_create(
                    project=project,
                    name=ms_name,
                    defaults=dict(
                        due_date=due,
                        planned_amt=amt,
                        status=MilestoneStatus.PLANNED,
                    ),
                )
                if not created:
                    ms.planned_amt += amt
                    ms.save(update_fields=["planned_amt"])

                txn_date = JalaliDate(year_fa, month_num, int(dc)).to_gregorian()

                to_create.append(Transaction(
                    company=company,
                    project=project,
                    category=cat,
                    milestone=ms,
                    import_ref=imp,
                    txn_date=txn_date,
                    amount=amt,
                    currency="IRR",
                ))

        # ── Bulk insert with tqdm (optional message) ────────────────────────
        self.stdout.write("🧾 Saving transactions to database…")
        Transaction.objects.bulk_create(to_create)

        imp.status = ImportStatus.COMPLETED
        imp.project = project
        imp.save(update_fields=["status", "project"])

        self.stdout.write(self.style.SUCCESS(
            f"✅ Imported {len(to_create)} transactions "
            f"and {Milestone.objects.filter(project=project).count()} milestones."
        ))

# python manage.py import_cashflow F:/cash flow/v0/Cash Flow - 20250521.xlsx --user-id 1
# python manage.py import_cashflow "docs/csv_import/Cash Flow-budgeted.xlsx" --user-id 1
# python manage.py import_cashflow "docs/csv_import/Cash Flow-Actual.xlsx" --user-id 1
# python manage.py import_cashflow "docs/csv_import/Cash Flow - 20250521.xlsx" --user-id 1