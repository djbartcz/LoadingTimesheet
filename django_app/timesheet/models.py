from django.db import models
from django.utils import timezone
import uuid


def generate_uuid():
    return str(uuid.uuid4())

class ActiveTimer(models.Model):
    """Currently running timers"""
    id = models.CharField(max_length=255, primary_key=True, default=generate_uuid)
    employee_id = models.CharField(max_length=255)
    employee_name = models.CharField(max_length=255)
    project_id = models.CharField(max_length=255, null=True, blank=True)
    project_name = models.CharField(max_length=255, null=True, blank=True)
    task = models.CharField(max_length=255)
    is_non_productive = models.BooleanField(default=False)
    is_break = models.BooleanField(default=False)
    start_time = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'active_timers'
        indexes = [
            models.Index(fields=['employee_id']),
        ]


class TimeRecord(models.Model):
    """Historical time records"""
    id = models.CharField(max_length=255, primary_key=True, default=generate_uuid)
    employee_id = models.CharField(max_length=255)
    employee_name = models.CharField(max_length=255)
    project_id = models.CharField(max_length=255, null=True, blank=True)
    project_name = models.CharField(max_length=255, null=True, blank=True)
    task = models.CharField(max_length=255)
    is_non_productive = models.BooleanField(default=False)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    duration_seconds = models.IntegerField(null=True, blank=True)
    ifs_sent = models.BooleanField(default=False)
    ifs_sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'time_records'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['start_time']),
        ]
        ordering = ['-end_time']


class Employee(models.Model):
    """Employee master data"""
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'employees'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.id} - {self.name}"


class Project(models.Model):
    """Project/Job number master data"""
    id = models.CharField(max_length=255, primary_key=True)
    name = models.CharField(max_length=255)
    project_description = models.CharField(max_length=500, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects'
        ordering = ['name']
    
    def __str__(self):
        if self.project_description:
            return f"{self.name} - {self.project_description}"
        return self.name


class Task(models.Model):
    """Task master data"""
    id = models.CharField(max_length=255, primary_key=True, default=generate_uuid)
    name = models.CharField(max_length=255)
    is_non_productive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['name']
        unique_together = [['name', 'is_non_productive']]
    
    def __str__(self):
        return self.name


# =============================================================================
# IFS Production Reporting - Staging Tables
# =============================================================================

class IfsOperationHistory(models.Model):
    """Labor reporting from manufacturing operations (base table)."""
    transaction_id = models.BigIntegerField(primary_key=True)
    transaction_code = models.CharField(max_length=50, blank=True, null=True)
    empno = models.CharField(max_length=50, blank=True, null=True)
    employee_name = models.CharField(max_length=255, blank=True, null=True)
    order_no = models.CharField(max_length=50, blank=True, null=True)
    work_center_no = models.CharField(max_length=50, blank=True, null=True)
    work_center_description = models.CharField(
        max_length=255, blank=True, null=True
    )
    part_no = models.CharField(max_length=100, blank=True, null=True)
    part_description = models.CharField(max_length=500, blank=True, null=True)
    labor_time = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    man_hours = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    transaction_date = models.DateTimeField(blank=True, null=True)
    order_type = models.CharField(max_length=50, blank=True, null=True)
    qty_complete = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    oper_status_code = models.CharField(max_length=50, blank=True, null=True)
    reversed_flag = models.CharField(max_length=50, blank=True, null=True)
    contract = models.CharField(max_length=50, blank=True, null=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ifs_operation_history'
        indexes = [
            models.Index(fields=['order_no', 'contract']),
            models.Index(fields=['empno']),
            models.Index(fields=['transaction_date']),
        ]

    def __str__(self):
        return f"OpHist {self.transaction_id}"


class IfsShopOrd(models.Model):
    """Shop order context."""
    order_no = models.CharField(max_length=50)
    release_no = models.CharField(max_length=50)
    sequence_no = models.CharField(max_length=50)
    contract = models.CharField(max_length=50, blank=True, null=True)
    part_no = models.CharField(max_length=100, blank=True, null=True)
    revised_qty_due = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    qty_complete = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    revised_due_date = models.DateTimeField(blank=True, null=True)
    need_date = models.DateTimeField(blank=True, null=True)
    cf_project = models.CharField(max_length=100, blank=True, null=True)
    cf_project_name = models.CharField(max_length=255, blank=True, null=True)
    cf_job_bom_item_name = models.CharField(
        max_length=255, blank=True, null=True
    )
    cf_length_mm = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ifs_shop_ord'
        unique_together = [['order_no', 'release_no', 'sequence_no']]
        indexes = [
            models.Index(fields=['order_no', 'release_no', 'sequence_no']),
            models.Index(fields=['contract']),
        ]

    def __str__(self):
        return f"ShopOrd {self.order_no}/{self.release_no}/{self.sequence_no}"


class IfsDopHead(models.Model):
    """DOP/project/planning context."""
    dop_id = models.CharField(max_length=100, primary_key=True)
    due_date = models.DateTimeField(blank=True, null=True)
    qty_demand = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    contract = models.CharField(max_length=50, blank=True, null=True)
    part_no = models.CharField(max_length=100, blank=True, null=True)
    description = models.CharField(max_length=500, blank=True, null=True)
    project_id = models.CharField(max_length=100, blank=True, null=True)
    project_name = models.CharField(max_length=255, blank=True, null=True)
    cf_project = models.CharField(max_length=100, blank=True, null=True)
    cf_project_name = models.CharField(max_length=255, blank=True, null=True)
    cf_job_bom_item_name = models.CharField(
        max_length=255, blank=True, null=True
    )
    cf_length_mm = models.DecimalField(
        max_digits=12, decimal_places=2, blank=True, null=True
    )
    cf_total_weight_kg = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    cf_hours_spend = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ifs_dop_head'
        indexes = [
            models.Index(fields=['part_no', 'contract']),
            models.Index(fields=['cf_project']),
        ]

    def __str__(self):
        return f"DOP {self.dop_id}"


class IfsProjectTransaction(models.Model):
    """Project accounting/cost reporting."""
    project_transaction_seq = models.BigIntegerField(primary_key=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    emp_no = models.CharField(max_length=50, blank=True, null=True)
    emp_name = models.CharField(max_length=255, blank=True, null=True)
    person_id = models.CharField(max_length=100, blank=True, null=True)
    account_date = models.DateField(blank=True, null=True)
    day_confirmed = models.CharField(max_length=50, blank=True, null=True)
    internal_quantity = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    internal_amount = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    resource_id = models.CharField(max_length=100, blank=True, null=True)
    report_cost_type = models.CharField(max_length=50, blank=True, null=True)
    project_id = models.CharField(max_length=100, blank=True, null=True)
    activity_no = models.CharField(max_length=100, blank=True, null=True)
    org_code = models.CharField(max_length=50, blank=True, null=True)
    origin_key1 = models.CharField(max_length=255, blank=True, null=True)
    origin_key_no1 = models.CharField(max_length=255, blank=True, null=True)
    activity_status = models.CharField(max_length=50, blank=True, null=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ifs_project_transaction'
        indexes = [
            models.Index(fields=['emp_no']),
            models.Index(fields=['project_id']),
            models.Index(fields=['account_date']),
        ]

    def __str__(self):
        return f"ProjTrans {self.project_transaction_seq}"


class IfsInventoryTransactionHist(models.Model):
    """Inventory/material movements linked to shop orders."""
    transaction_id = models.BigIntegerField(primary_key=True)
    date_applied = models.DateTimeField(blank=True, null=True)
    part_no = models.CharField(max_length=100, blank=True, null=True)
    part_description = models.CharField(max_length=500, blank=True, null=True)
    transaction_code = models.CharField(max_length=50, blank=True, null=True)
    transaction_code_desc = models.CharField(
        max_length=255, blank=True, null=True
    )
    quantity = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    cost = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    inventory_cost = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    total_cost = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )
    contract = models.CharField(max_length=50, blank=True, null=True)
    location_no = models.CharField(max_length=100, blank=True, null=True)
    lot_batch_no = models.CharField(max_length=100, blank=True, null=True)
    source_ref1 = models.CharField(max_length=100, blank=True, null=True)
    source_ref2 = models.CharField(max_length=100, blank=True, null=True)
    source_ref3 = models.CharField(max_length=100, blank=True, null=True)
    userid = models.CharField(max_length=100, blank=True, null=True)
    fetched_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ifs_inventory_transaction_hist'
        indexes = [
            models.Index(
                fields=['source_ref1', 'source_ref2', 'source_ref3']
            ),
            models.Index(fields=['part_no', 'contract']),
            models.Index(fields=['date_applied']),
        ]

    def __str__(self):
        return f"InvTrans {self.transaction_id}"


class IfsReportData(models.Model):
    """Final combined reporting table."""
    id = models.BigAutoField(primary_key=True)
    transaction_id = models.BigIntegerField()
    employee_id = models.CharField(max_length=50, blank=True, null=True)
    employee_name = models.CharField(max_length=255, blank=True, null=True)
    transaction_code = models.CharField(max_length=50, blank=True, null=True)
    transaction_date = models.DateTimeField(blank=True, null=True)

    order_no = models.CharField(max_length=50, blank=True, null=True)
    release_no = models.CharField(max_length=50, blank=True, null=True)
    sequence_no = models.CharField(max_length=50, blank=True, null=True)
    contract = models.CharField(max_length=50, blank=True, null=True)

    labor_part_no = models.CharField(max_length=100, blank=True, null=True)
    labor_time = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    man_hours = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )

    shop_part_no = models.CharField(max_length=100, blank=True, null=True)
    revised_qty_due = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    shop_qty_complete = models.DecimalField(
        max_digits=12, decimal_places=4, blank=True, null=True
    )
    need_date = models.DateTimeField(blank=True, null=True)
    cf_project = models.CharField(max_length=100, blank=True, null=True)
    cf_project_name = models.CharField(max_length=255, blank=True, null=True)
    cf_job_bom_item_name = models.CharField(
        max_length=255, blank=True, null=True
    )

    inv_transaction_id = models.BigIntegerField(blank=True, null=True)
    inv_transaction_code = models.CharField(
        max_length=50, blank=True, null=True
    )
    inv_date_applied = models.DateTimeField(blank=True, null=True)
    inv_part_no = models.CharField(max_length=100, blank=True, null=True)
    inv_quantity = models.DecimalField(
        max_digits=14, decimal_places=4, blank=True, null=True
    )

    built_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ifs_report_data'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['order_no']),
            models.Index(fields=['transaction_date']),
            models.Index(fields=['cf_project']),
        ]

    def __str__(self):
        return f"Report {self.transaction_id}"
