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
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'projects'
        ordering = ['name']
    
    def __str__(self):
        return f"{self.id} - {self.name}"


class Task(models.Model):
    """Task master data"""
    name = models.CharField(max_length=255, primary_key=True)
    is_non_productive = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'tasks'
        ordering = ['name']
    
    def __str__(self):
        return self.name
