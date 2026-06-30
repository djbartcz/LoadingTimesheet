"""
Management command to sync IFS production reporting data.

Calls IFS OData endpoints and stores data into staging tables.

Usage:
    python manage.py sync_ifs_reporting
    python manage.py sync_ifs_reporting --only=shop_ord,shop_oper_clocking
"""

import logging
from datetime import datetime, timezone as dt_timezone
from decimal import Decimal, InvalidOperation

from django.core.management.base import BaseCommand
from django.db import transaction

from timesheet.ifs_api_connector import IFSAPIConnector
from timesheet.models import (
    IfsDopHead,
    IfsEmployeeDirectory,
    IfsInventoryTransactionHist,
    IfsProjectTransaction,
    IfsShopOperClocking,
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
        "&use-default-filter=false&use-timezone-filter=false"
    ),
    # NOT USED by Production Dashboard (Daily Labour / Project Dashboard).
    # Kept only for potential future reporting needs.
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
    # NOT USED by Production Dashboard (Daily Labour / Project Dashboard).
    # Kept only for potential future reporting needs.
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
    "employees": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/EmployeesHandling.svc/CompanyPersons?"
        "$orderby=CompanyId,EmpNo"
        "&$select=EmpNo,EmployeeStatus,CompanyId,Fname,Lname,"
        "InternalDisplayName,ExternalDisplayName,luname,keyref"
        "&use-timezone-filter=false"
    ),
    "shop_oper_clocking": (
        "https://groupebriand.ifs.cloud/main/ifsapplications/"
        "projection/v1/ShopFloorClockingsHandling.svc/ShopOperClockingUtilSet?"
        "$select=ClockingSeq,Company,OrderNo,OperationNo,TransactionId,"
        "TransactionDate,EmployeeId,CreatedByEmployeeId,ClockingType,CrewSize,"
        "WorkCenterNo,PartDescription,Duration,luname,keyref"
        "&$expand=EmployeeIdRef($select=Name,luname,keyref),"
        "ShopOrdRef($select=PartNo,luname,keyref),"
        "ShopOrderOperationRef($select=RevisedQtyDue,luname,keyref)"
        "&use-default-filter=true&use-timezone-filter=false"
    ),
}

# Sources currently used by Production Dashboard tabs:
# - Daily Labour: shop_oper_clocking + employees
# - Project Dashboard: shop_ord + dop_head + shop_oper_clocking + time_records(local)
USED_SOURCES = [
    'shop_oper_clocking',
    'employees',
    'shop_ord',
    'dop_head',
]

# Default sync updates only sources used by current dashboards.
# Other sources can still be synced explicitly via --only=...
ALL_SOURCES = USED_SOURCES


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
            '--only',
            type=str,
            default='',
            help='Comma-separated list of sources to sync',
        )

    def handle(self, *args, **options):
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
            'project_transaction': self._upsert_project_transaction,
            'inventory_transaction': self._upsert_inventory_transaction,
            'employees': self._upsert_employees,
            'shop_oper_clocking': self._upsert_shop_oper_clocking,
        }
        handler = handlers[source]
        return handler(records)

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

    def _upsert_employees(self, records):
        count = 0
        for row in records:
            emp_no = str(row.get('EmpNo') or '').strip()
            if not emp_no:
                continue
            IfsEmployeeDirectory.objects.update_or_create(
                emp_no=emp_no,
                defaults={
                    'company_id': row.get('CompanyId'),
                    'employee_status': row.get('EmployeeStatus'),
                    'first_name': row.get('Fname'),
                    'last_name': row.get('Lname'),
                    'internal_display_name': row.get('InternalDisplayName'),
                    'external_display_name': row.get('ExternalDisplayName'),
                },
            )
            count += 1
        return count

    def _upsert_shop_oper_clocking(self, records):
        count = 0
        for row in records:
            clocking_seq = row.get('ClockingSeq')
            if not clocking_seq:
                continue
            shop_op_ref = row.get('ShopOrderOperationRef') or {}
            employee_ref = row.get('EmployeeIdRef') or {}
            shop_ord_ref = row.get('ShopOrdRef') or {}
            employee_id = str(row.get('EmployeeId') or '').strip() or None
            created_by_employee_id = (
                str(row.get('CreatedByEmployeeId') or '').strip() or None
            )
            IfsShopOperClocking.objects.update_or_create(
                clocking_seq=clocking_seq,
                defaults={
                    'company': row.get('Company'),
                    'order_no': row.get('OrderNo'),
                    'operation_no': row.get('OperationNo'),
                    'transaction_id': row.get('TransactionId'),
                    'transaction_date': parse_date(row.get('TransactionDate')),
                    'employee_id': employee_id,
                    'employee_name': employee_ref.get('Name'),
                    'created_by_employee_id': created_by_employee_id,
                    'clocking_type': row.get('ClockingType'),
                    'crew_size': parse_decimal(row.get('CrewSize')),
                    'work_center_no': row.get('WorkCenterNo'),
                    'part_no': shop_ord_ref.get('PartNo'),
                    'part_description': row.get('PartDescription'),
                    # Prefer ShopOrderOperationRef.RevisedQtyDue as requested.
                    # Fallback to OperationQty when available.
                    'operation_qty': parse_decimal(
                        shop_op_ref.get('RevisedQtyDue') or row.get('OperationQty')
                    ),
                    'duration': parse_decimal(row.get('Duration')),
                },
            )
            count += 1
        return count

