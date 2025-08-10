import json
import logging
import sys
import time
import traceback

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

import mysql.connector
from autocare_pcadb.models import *

from rich.console import Console, Group
from rich.live import Live
from rich.text import Text
from rich.progress_bar import ProgressBar

logger = logging.getLogger(__name__)
console = Console()

MAX_WIDTH = 80  # hard cap for all printed lines


class Command(BaseCommand):
    help = 'Migrate data from MySQL to PostgreSQL'

    # Tunables
    READ_CHUNK = 20000          # rows per fetchmany()
    INSERT_BATCH_SIZE = 20000   # rows per bulk_create

    def add_arguments(self, parser):
        parser.add_argument('--mysql-host', type=str, default=None, help='MySQL host')
        parser.add_argument('--mysql-db', type=str, default=None, help='MySQL database name')
        parser.add_argument('--mysql-user', type=str, default=None, help='MySQL username')
        parser.add_argument('--mysql-password', type=str, default=None, help='MySQL password')

    def handle(self, *args, **options):
        self.stdout.write('Starting MySQL to PostgreSQL migration...')

        mysql_host = options['mysql_host'] or settings.AUTOCARE_DB_HOST
        mysql_database = options['mysql_db'] or settings.AUTOCARE_DB_NAME_PCADB
        mysql_user = options['mysql_user'] or settings.AUTOCARE_DB_USER
        mysql_password = options['mysql_password'] or settings.AUTOCARE_DB_PASSWORD

        try:
            mysql_conn = mysql.connector.connect(
                host=mysql_host,
                database=mysql_database,
                user=mysql_user,
                password=mysql_password,
            )
            meta = mysql_conn.cursor(dictionary=True)

            meta.execute("SET foreign_key_checks = 0;")

            # Gather tables
            meta.execute("SHOW TABLES")
            table_rows = meta.fetchall()
            all_table_names = [t[f'Tables_in_{mysql_database}'] for t in table_rows]

            # Filter to tables with matching models; pre-count totals and compute global widths
            included = []
            totals = {}
            max_total = 0
            max_label_len = 0

            def label_for(name, mdl):
                return f"{name} → {mdl.__name__}"

            for name in all_table_names:
                mdl = self.get_model_by_table_name(name)
                if not mdl:
                    logger.warning(f"Model for table {name} not found, skipping.")
                    continue
                total = self._count_rows(mysql_conn, name)
                totals[name] = total
                max_total = max(max_total, total)
                max_label_len = max(max_label_len, len(label_for(name, mdl)))
                included.append((name, mdl))

            if not included:
                self.stdout.write(self.style.WARNING("No matching tables/models found."))
                return

            # ---------- GLOBAL FIXED WIDTHS (stable across all tables) ----------
            def comma_width(n: int) -> int:
                return len(f"{n:,}")

            count_w = max(1, comma_width(max_total))             # width of comma-formatted max total
            done_total_w = count_w * 2 + 1                       # "<done>/<total>"
            pct_w = 7                                            # "100.00%"
            # Bar width for line 2: "<bar> <pct>%  <done/total>"
            # total <= MAX_WIDTH; use spaces count: 1 (after bar) + 1 (between % and done/total)
            bar_w = MAX_WIDTH - (1 + pct_w + 1 + done_total_w)
            if bar_w < 10:
                # ensure a minimum sensible bar
                bar_w = 10

            # Line 1: "Table: <label>"
            # Reserve len("Table: ") = 7
            label_w = MAX_WIDTH - 7
            # --------------------------------------------------------------------

            with transaction.atomic():
                for table_name, model in included:
                    self._migrate_table(
                        mysql_conn=mysql_conn,
                        mysql_table_name=table_name,
                        model=model,
                        total_rows=totals[table_name],
                        # global widths
                        label_w=label_w,
                        bar_w=bar_w,
                        pct_w=pct_w,
                        done_total_w=done_total_w,
                        count_w=count_w,
                    )

                self.stdout.write(self.style.SUCCESS('Migration completed successfully!'))

            meta.execute("SET foreign_key_checks = 1;")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Migration failed: {str(e)}'))
            raise
        finally:
            try:
                meta.close()
            except Exception:
                pass
            try:
                mysql_conn.close()
            except Exception:
                pass

    def get_model_by_table_name(self, mysql_table_name):
        # Expect your model class to be importable and named exactly like the table
        return globals().get(mysql_table_name)

    # ------------------------- Core Migration -------------------------

    def _migrate_table(
        self,
        mysql_conn,
        mysql_table_name,
        model,
        total_rows,
        label_w,
        bar_w,
        pct_w,
        done_total_w,
        count_w,
    ):
        """Stream, batch, fixed 80-col, 3-line panel, and full error rows."""
        src = mysql_conn.cursor(dictionary=True)
        src.arraysize = self.READ_CHUNK
        src.execute(f"SELECT * FROM `{mysql_table_name}`")

        # Precompute mapping
        field_map = []
        for f in model._meta.fields:
            src_col = f.db_column or f.name
            if f.is_relation and f.many_to_one:
                field_map.append(("fk", f.attname, src_col))
            else:
                field_map.append(("val", f.name, src_col))

        pk_dbcol = getattr(model._meta.pk, "db_column", None) or model._meta.pk.name

        # Helpers for rendering within 80 columns
        def trunc_label(s: str) -> str:
            if len(s) <= label_w:
                return s.ljust(label_w)
            # leave space for ellipsis
            return s[: max(0, label_w - 1)] + "…"

        def pct_color(frac: float) -> str:
            if frac >= 0.80:
                return "green"
            if frac >= 0.50:
                return "yellow"
            return "cyan"

        def fmt_int(n: int) -> str:
            return f"{n:,}"

        def fmt_time(seconds: float) -> str:
            s = max(0, int(seconds))
            if s >= 3600:
                return f"{s//3600:02d}:{(s%3600)//60:02d}"
            return f"{s//60:02d}:{s%60:02d}"

        def render_panel(done: int, inserted: int, errors: int, start_ts: float):
            # Line 1: Table label
            label = f"{mysql_table_name} → {model.__name__}"
            line1 = Text(f"Table: {trunc_label(label)}")

            # Line 2: bar + pct + done/total (fixed widths)
            total = max(total_rows, 1)
            done = min(done, total_rows)
            frac = (done / total) if total_rows else 0.0

            bar = ProgressBar(total=total, completed=done, width=bar_w)
            pct_txt = Text(f"{frac*100:>{pct_w}.2f}%", style=pct_color(frac))
            done_total_txt = f"{fmt_int(done):>{done_total_w - (count_w + 1)}}/{fmt_int(total_rows):>{count_w}}"

            # Compose line 2 with exact spacing: "<bar> <pct> <done/total>"
            # (bar is a renderable, so put pieces into a Group)
            # We keep a single space between components to stay within 80 cols.
            line2 = Group(bar, Text(" "), pct_txt, Text(" "), Text(done_total_txt))

            # Line 3: rate/s, elapsed, ETA, inserted, errors (fixed widths, compact)
            elapsed = time.time() - start_ts
            rate = (done / elapsed) if elapsed > 0 else 0.0
            remain = max(0, total_rows - done)
            eta = (remain / rate) if rate > 0 else 0.0

            # Build compact metrics string and trim exactly to MAX_WIDTH if needed
            metrics = (
                f"rate/s {int(rate):>6,d}  "
                f"elapsed {fmt_time(elapsed):>5}  "
                f"eta {fmt_time(eta):>5}  "
                f"ins {fmt_int(inserted):>{count_w}}  "
                f"err {fmt_int(errors):>{count_w}}"
            )
            if len(metrics) > MAX_WIDTH:
                metrics = metrics[:MAX_WIDTH]

            # Colorize "err" number if nonzero
            if errors:
                # find the start index of the error count and split
                err_str = f"{fmt_int(errors):>{count_w}}"
                prefix = metrics[:-count_w]
                line3 = Group(Text(prefix), Text(err_str, style="red"))
            else:
                line3 = Text(metrics)

            return Group(line1, line2, line3)

        total_seen = 0
        total_inserted = 0
        total_errors = 0
        start_ts = time.time()

        # Initial render
        panel = render_panel(0, 0, 0, start_ts)

        with Live(panel, console=console, refresh_per_second=8, vertical_overflow="visible") as live:
            while True:
                rows = src.fetchmany(self.READ_CHUNK)
                if not rows:
                    break
                total_seen += len(rows)

                for i in range(0, len(rows), self.INSERT_BATCH_SIZE):
                    sub = rows[i:i + self.INSERT_BATCH_SIZE]
                    inserted, errors = self._insert_batch(model, field_map, sub, pk_dbcol)
                    total_inserted += inserted
                    total_errors += errors

                    # Rebuild the panel with updated values
                    panel = render_panel(
                        min(total_seen, total_rows),
                        total_inserted,
                        total_errors,
                        start_ts
                    )

                    # Tell Live to refresh the display
                    live.update(panel)

        # Final summary line (kept short)
        if total_errors == 0:
            console.print(f"[bold green]✓ {mysql_table_name} → {model.__name__}[/] "
                          f"inserted {total_inserted:,}, errors 0")
        else:
            console.print(f"[bold yellow]✓ (with warnings) {mysql_table_name} → {model.__name__}[/] "
                          f"inserted {total_inserted:,}, errors [red]{total_errors:,}[/]")

        try:
            src.close()
        except Exception:
            pass

    # ------------------------- Helpers -------------------------

    def _count_rows(self, mysql_conn, table_name) -> int:
        cur = mysql_conn.cursor()
        try:
            cur.execute(f"SELECT COUNT(*) FROM `{table_name}`")
            return int(cur.fetchone()[0] or 0)
        finally:
            try:
                cur.close()
            except Exception:
                pass

    def _map_row(self, field_map, row_dict):
        data = {}
        for kind, target, source in field_map:
            if source not in row_dict:
                continue
            v = row_dict[source]
            if isinstance(v, str):
                v = v.strip()
            if kind == "fk":
                data[target] = v
            else:
                data[target] = v
        return data

    def _build_instances(self, model, field_map, rows, pk_dbcol):
        instances = []
        for r in rows:
            try:
                instances.append(model(**self._map_row(field_map, r)))
            except Exception as e:
                mysql_pk = r.get(pk_dbcol, None)
                console.print(
                    "[red][MAP ERROR][/red] "
                    f"{model._meta.db_table or model.__name__}: "
                    f"MySQL {pk_dbcol}={mysql_pk} → {e.__class__.__name__}: {e}"
                )
                logger.exception("Mapping error for row", extra={"mysql_pk": mysql_pk})
                self._print_row_details(r, self._map_row(field_map, r))
        return instances

    def _insert_batch(self, model, field_map, rows, pk_dbcol):
        if not rows:
            return 0, 0

        @transaction.atomic
        def try_insert(batch):
            instances = self._build_instances(model, field_map, batch, pk_dbcol)
            if not instances:
                return 0
            model.objects.bulk_create(instances, ignore_conflicts=True, batch_size=len(instances))
            return len(instances)

        try:
            inserted = try_insert(rows)
            return inserted, 0
        except Exception:
            return self._bisect_and_log(model, field_map, rows, pk_dbcol)

    def _bisect_and_log(self, model, field_map, rows, pk_dbcol):
        inserted_total = 0
        errors_total = 0

        if len(rows) == 1:
            r = rows[0]
            try:
                with transaction.atomic():
                    model.objects.bulk_create(
                        [model(**self._map_row(field_map, r))],
                        ignore_conflicts=True,
                        batch_size=1,
                    )
                    return 1, 0
            except Exception as e:
                mysql_pk = r.get(pk_dbcol, None)
                console.print(
                    f"[red][INSERT ERROR][/red] {model._meta.db_table or model.__name__}: "
                    f"MySQL {pk_dbcol}={mysql_pk} → {e.__class__.__name__}: {e}"
                )
                logger.exception("Insert error for row", extra={"mysql_pk": mysql_pk})
                self._print_row_details(r, self._map_row(field_map, r))
                return 0, 1

        mid = len(rows) // 2
        left, right = rows[:mid], rows[mid:]

        try:
            with transaction.atomic():
                instances = self._build_instances(model, field_map, left, pk_dbcol)
                if instances:
                    model.objects.bulk_create(instances, ignore_conflicts=True, batch_size=len(instances))
                    inserted_total += len(instances)
        except Exception:
            ins_l, err_l = self._bisect_and_log(model, field_map, left, pk_dbcol)
            inserted_total += ins_l
            errors_total += err_l

        try:
            with transaction.atomic():
                instances = self._build_instances(model, field_map, right, pk_dbcol)
                if instances:
                    model.objects.bulk_create(instances, ignore_conflicts=True, batch_size=len(instances))
                    inserted_total += len(instances)
        except Exception:
            ins_r, err_r = self._bisect_and_log(model, field_map, right, pk_dbcol)
            inserted_total += ins_r
            errors_total += err_r

        return inserted_total, errors_total

    def _print_row_details(self, mysql_row, mapped_data):
        try:
            console.print("[bold]Source row (MySQL column → value):[/]")
            console.print_json(json.dumps(mysql_row, default=str))
        except Exception:
            console.print(str(mysql_row))

        try:
            console.print("[bold]Mapped data (Django field → value):[/]")
            console.print_json(json.dumps(mapped_data, default=str))
        except Exception:
            console.print(str(mapped_data))
