"""
Management command to sync IFS production reporting data.

Calls IFS OData endpoints, stores into staging tables, and builds
the final report_data table using validated joins.

Usage:
    python manage.py sync_ifs_reporting
    python manage.py sync_ifs_reporting --skip-report
    python manage.py sync_ifs_reporting --only=operation_history,shop_ord
"""

import logging
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.utils import timezone

from timesheet.ifs_api_connector import IFSAPIConnector
from timesheet.models import (
    IfsDopHead,
    IfsInventoryTransactionHist,
    IfsOperationHistory,
    IfsProjectTransaction,
    IfsReportData,
    IfsShopOrd,
)

logger = logging.getLogger(__name__)

ENDPOINTS = {
    "dop_head": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/DopHeadersHandling.svc/DopHeadSet?"
        "$select=DopId,DueDate,QtyDemand,Contract,PartNo,Description,"
        "ProjectId,ProjectName,Cf_Project,Cf_Project_Name,"
        "Cf_Job_Bom_Item_Name,Cf_Length_Mm,Cf_Total_Weight_Kg,"
        "Cf_Hours_Spend,luname,keyref"
        "&use-timezone-filter=false"
    ),
    "shop_ord": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/ShopOrdersHandling.svc/ShopOrds?"
        "$select=OrderNo,ReleaseNo,SequenceNo,Contract,PartNo,"
        "RevisedQtyDue,QtyComplete,RevisedDueDate,NeedDate,"
        "Cf_Project,Cf_Project_Name,Cf_Job_Bom_Item_Name,Cf_Length_Mm,"
        "luname,keyref"
        "&use-default-filter=true&use-timezone-filter=false"
    ),
    "operation_history": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/LaborAndOperationHistoryHandling.svc/"
        "OperationHistorys?"
        "$select=TransactionId,TransactionCode,Empno,EmployeeName,"
        "OrderNo,WorkCenterNo,PartNo,PartDescription,LaborTime,"
        "ManHours,TransactionDate,OrderType,QtyComplete,"
        "OperStatusCode,ReversedFlag,Contract,luname,keyref"
        "&$expand=WorkCenterRef($select=Description,Objgrants,"
        "Contract,luname,keyref)"
        "&use-default-filter=true&use-timezone-filter=false"
    ),
    "project_transaction": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/ProjectTransactionsHandling.svc/"
        "ProjectTransactionSet?"
        "$filter=(CompanyId%20eq%20%2751%27)"
        "&$select=ProjectTransactionSeq,CompanyId,EmpNo,AccountDate,"
        "DayConfirmed,InternalQuantity,InternalAmount,ResourceId,"
        "ReportCostType,ProjectId,ActivityNo,OrgCode,OriginKey1,"
        "OriginKeyNo1,ActivityStatus,luname,keyref"
        "&$expand=EmpNoPerfRef($select=Name,PersonId,luname,keyref)"
        "&use-default-filter=true&use-timezone-filter=false"
    ),
    "inventory_transaction": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/InventoryTransactionsHistoryHandling.svc/"
        "InventoryTransactionsHistorySet?"
        "$filter=((startswith(Contract%2C%275402%27)))"
        "&$orderby=TransactionId%20desc"
        "&$select=TransactionId,DateApplied,PartNo,PartDescription,"
        "TransactionCode,TransactionCodeDesc,Quantity,Cost,"
        "InventoryCost,TotalCost,Contract,LocationNo,LotBatchNo,"
        "SourceRef1,SourceRef2,SourceRef3,Userid,luname,keyref"
        "&use-timezone-filter=false"
    ),
}

ALL_SOURCES = list(ENDPOINTS.keys())


def parse_decimal(value):
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=dt_timezone.utc)
        return value
    text = str(value).strip()
    for fmt in (
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M:%SZ",
        "%Y-%m-%dT%H:%M:%S.%f",
        "%Y-%m-%dT%H:%M:%S.%fZ",
        "%Y-%m-%d",
    ):
        try:
            dt = datetime.strptime(text[:len(fmt) + 5], fmt)
            return dt.replace(tzinfo=dt_timezone.utc)
        except (ValueError, IndexError):
            continue
    return None


def parse_date(value):
    dt = parse_datetime(value)
    if dt:
        return dt.date()
    return None


class Command(BaseCommand):
    help = "Sync IFS production reporting data into staging tables"

    def add_arguments(self, parser):
        parser.add_argument(
            '--skip-report',
            action='store_true',
            help='Skip building the final report_data table',
        )
        parser.add_argument(
            '--only',
            type=str,
            default='',
            help='Comma-separated list of sources to sync',
        )

    def handle(self, *args, **options):
        skip_report = options['skip_report']
        only = [
            s.strip() for s in options['only'].split(',') if s.strip()
        ]
        sources = only if only else ALL_SOURCES

        connector = IFSAPIConnector()
        self.stdout.write("Starting IFS reporting data sync...")

        for source in sources:
            if source not in ENDPOINTS:
                self.stderr.write(f"Unknown source: {source}")
                continue
            self.stdout.write(f"  Fetching {source}...")
            try:
                data = self._fetch_all_pages(connector, ENDPOINTS[source])
                count = self._upsert(source, data)
                self.stdout.write(
                    self.style.SUCCESS(f"    {source}: {count} rows upserted")
                )
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"    {source} FAILED: {exc}")
                )
                logger.error("Sync %s failed: %s", source, exc, exc_info=True)

        if not skip_report:
            self.stdout.write("  Building report_data...")
            try:
                count = self._build_report()
                self.stdout.write(
                    self.style.SUCCESS(f"    report_data: {count} rows built")
                )
            except Exception as exc:
                self.stderr.write(
                    self.style.ERROR(f"    report_data FAILED: {exc}")
                )
                logger.error("Build report failed: %s", exc, exc_info=True)

        self.stdout.write(self.style.SUCCESS("Sync complete."))

    def _fetch_all_pages(self, connector, url):
        """Fetch all pages from an OData endpoint."""
        all_records = []
        next_url = url
        page = 0
        while next_url:
            page += 1
            response = connector.get(next_url)
            response.raise_for_status()
            payload = response.json()
            records = payload.get('value', [])
            all_records.extend(records)
            next_url = payload.get('@odata.nextLink')
            if page % 5 == 0:
                self.stdout.write(
                    f"      page {page}, {len(all_records)} records so far..."
                )
        return all_records

    @transaction.atomic
    def _upsert(self, source, records):
        """Route to appropriate upsert handler."""
        handlers = {
            'dop_head': self._upsert_dop_head,
            'shop_ord': self._upsert_shop_ord,
            'operation_history': self._upsert_operation_history,
            'project_transaction': self._upsert_project_transaction,
            'inventory_transaction': self._upsert_inventory_transaction,
        }
        handler = handlers[source]
        return handler(records)

    def _upsert_operation_history(self, records):
        count = 0
        for row in records:
            tid = row.get('TransactionId')
            if not tid:
                continue
            wc_ref = row.get('WorkCenterRef') or {}
            IfsOperationHistory.objects.update_or_create(
                transaction_id=tid,
                defaults={
                    'transaction_code': row.get('TransactionCode'),
                    'empno': row.get('Empno'),
                    'employee_name': row.get('EmployeeName'),
                    'order_no': row.get('OrderNo'),
                    'work_center_no': row.get('WorkCenterNo'),
                    'work_center_description': wc_ref.get('Description'),
                    'part_no': row.get('PartNo'),
                    'part_description': row.get('PartDescription'),
                    'labor_time': parse_decimal(row.get('LaborTime')),
                    'man_hours': parse_decimal(row.get('ManHours')),
                    'transaction_date': parse_datetime(
                        row.get('TransactionDate')
                    ),
                    'order_type': row.get('OrderType'),
                    'qty_complete': parse_decimal(row.get('QtyComplete')),
                    'oper_status_code': row.get('OperStatusCode'),
                    'reversed_flag': row.get('ReversedFlag'),
                    'contract': row.get('Contract'),
                },
            )
            count += 1
        return count

    def _upsert_shop_ord(self, records):
        count = 0
        for row in records:
            order_no = row.get('OrderNo')
            release_no = str(row.get('ReleaseNo') or '')
            sequence_no = str(row.get('SequenceNo') or '')
            if not order_no:
                continue
            IfsShopOrd.objects.update_or_create(
                order_no=order_no,
                release_no=release_no,
                sequence_no=sequence_no,
                defaults={
                    'contract': row.get('Contract'),
                    'part_no': row.get('PartNo'),
                    'revised_qty_due': parse_decimal(
                        row.get('RevisedQtyDue')
                    ),
                    'qty_complete': parse_decimal(row.get('QtyComplete')),
                    'revised_due_date': parse_datetime(
                        row.get('RevisedDueDate')
                    ),
                    'need_date': parse_datetime(row.get('NeedDate')),
                    'cf_project': row.get('Cf_Project'),
                    'cf_project_name': row.get('Cf_Project_Name'),
                    'cf_job_bom_item_name': row.get('Cf_Job_Bom_Item_Name'),
                    'cf_length_mm': parse_decimal(row.get('Cf_Length_Mm')),
                },
            )
            count += 1
        return count

    def _upsert_dop_head(self, records):
        count = 0
        for row in records:
            dop_id = row.get('DopId')
            if not dop_id:
                continue
            IfsDopHead.objects.update_or_create(
                dop_id=str(dop_id),
                defaults={
                    'due_date': parse_datetime(row.get('DueDate')),
                    'qty_demand': parse_decimal(row.get('QtyDemand')),
                    'contract': row.get('Contract'),
                    'part_no': row.get('PartNo'),
                    'description': row.get('Description'),
                    'project_id': row.get('ProjectId'),
                    'project_name': row.get('ProjectName'),
                    'cf_project': row.get('Cf_Project'),
                    'cf_project_name': row.get('Cf_Project_Name'),
                    'cf_job_bom_item_name': row.get('Cf_Job_Bom_Item_Name'),
                    'cf_length_mm': parse_decimal(row.get('Cf_Length_Mm')),
                    'cf_total_weight_kg': parse_decimal(
                        row.get('Cf_Total_Weight_Kg')
                    ),
                    'cf_hours_spend': parse_decimal(
                        row.get('Cf_Hours_Spend')
                    ),
                },
            )
            count += 1
        return count

    def _upsert_project_transaction(self, records):
        count = 0
        for row in records:
            seq = row.get('ProjectTransactionSeq')
            if not seq:
                continue
            emp_ref = row.get('EmpNoPerfRef') or {}
            IfsProjectTransaction.objects.update_or_create(
                project_transaction_seq=seq,
                defaults={
                    'company_id': row.get('CompanyId'),
                    'emp_no': row.get('EmpNo'),
                    'emp_name': emp_ref.get('Name'),
                    'person_id': emp_ref.get('PersonId'),
                    'account_date': parse_date(row.get('AccountDate')),
                    'day_confirmed': row.get('DayConfirmed'),
                    'internal_quantity': parse_decimal(
                        row.get('InternalQuantity')
                    ),
                    'internal_amount': parse_decimal(
                        row.get('InternalAmount')
                    ),
                    'resource_id': row.get('ResourceId'),
                    'report_cost_type': row.get('ReportCostType'),
                    'project_id': row.get('ProjectId'),
                    'activity_no': row.get('ActivityNo'),
                    'org_code': row.get('OrgCode'),
                    'origin_key1': row.get('OriginKey1'),
                    'origin_key_no1': row.get('OriginKeyNo1'),
                    'activity_status': row.get('ActivityStatus'),
                },
            )
            count += 1
        return count

    def _upsert_inventory_transaction(self, records):
        count = 0
        for row in records:
            tid = row.get('TransactionId')
            if not tid:
                continue
            IfsInventoryTransactionHist.objects.update_or_create(
                transaction_id=tid,
                defaults={
                    'date_applied': parse_datetime(row.get('DateApplied')),
                    'part_no': row.get('PartNo'),
                    'part_description': row.get('PartDescription'),
                    'transaction_code': row.get('TransactionCode'),
                    'transaction_code_desc': row.get('TransactionCodeDesc'),
                    'quantity': parse_decimal(row.get('Quantity')),
                    'cost': parse_decimal(row.get('Cost')),
                    'inventory_cost': parse_decimal(
                        row.get('InventoryCost')
                    ),
                    'total_cost': parse_decimal(row.get('TotalCost')),
                    'contract': row.get('Contract'),
                    'location_no': row.get('LocationNo'),
                    'lot_batch_no': row.get('LotBatchNo'),
                    'source_ref1': row.get('SourceRef1'),
                    'source_ref2': row.get('SourceRef2'),
                    'source_ref3': row.get('SourceRef3'),
                    'userid': row.get('Userid'),
                },
            )
            count += 1
        return count

    @transaction.atomic
    def _build_report(self):
        """Build report_data from staging tables using validated joins."""
        IfsReportData.objects.all().delete()

        sql = """
            INSERT INTO ifs_report_data (
                transaction_id, employee_id, employee_name,
                transaction_code, transaction_date,
                order_no, release_no, sequence_no, contract,
                labor_part_no, labor_time, man_hours,
                shop_part_no, revised_qty_due, shop_qty_complete,
                need_date, cf_project, cf_project_name,
                cf_job_bom_item_name,
                inv_transaction_id, inv_transaction_code,
                inv_date_applied, inv_part_no, inv_quantity,
                built_at
            )
            SELECT
                oh.transaction_id,
                oh.empno,
                oh.employee_name,
                oh.transaction_code,
                oh.transaction_date,

                oh.order_no,
                so.release_no,
                so.sequence_no,
                oh.contract,

                oh.part_no,
                oh.labor_time,
                oh.man_hours,

                so.part_no,
                so.revised_qty_due,
                so.qty_complete,
                so.need_date,
                so.cf_project,
                so.cf_project_name,
                so.cf_job_bom_item_name,

                inv.transaction_id,
                inv.transaction_code,
                inv.date_applied,
                inv.part_no,
                inv.quantity,

                NOW()
            FROM ifs_operation_history oh
            LEFT JOIN ifs_shop_ord so
                ON oh.order_no = so.order_no
                AND so.release_no IS NOT NULL
                AND so.sequence_no IS NOT NULL
                AND oh.contract = so.contract
            LEFT JOIN ifs_inventory_transaction_hist inv
                ON oh.order_no = inv.source_ref1
                AND oh.part_no = inv.part_no
                AND oh.contract = inv.contract
            WHERE oh.contract = '5402'
              AND oh.transaction_code = 'LABOR_RPT'
              AND oh.empno IS NOT NULL
        """
        with connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.rowcount
