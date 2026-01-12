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
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'time_records'
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['start_time']),
        ]
        ordering = ['-end_time']
