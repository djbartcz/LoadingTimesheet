"""
URL configuration for timesheet_project project.
"""
from django.contrib import admin
from django.urls import path
from timesheet import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.employee_selection, name='employee_selection'),
    path(
        'employee/<str:employee_id>/',
        views.timer_page,
        name='timer_page',
    ),
    path(
        'employee/<str:employee_id>/start/',
        views.start_timer,
        name='start_timer',
    ),
    path(
        'employee/<str:employee_id>/stop/',
        views.stop_timer,
        name='stop_timer',
    ),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/sync/', views.sync_to_excel, name='sync_to_excel'),
    path('admin-dashboard/export/', views.export_to_excel, name='export_to_excel'),
    path('detail-dashboard/', views.detail_dashboard, name='detail_dashboard'),
    path(
        'detail-dashboard/refresh/',
        views.detail_dashboard_refresh,
        name='detail_dashboard_refresh',
    ),
    path('admin-control/', views.admin_control_panel, name='admin_control_panel'),
    path('admin-control/save/', views.save_master_data, name='save_master_data'),
    path(
        'admin-control/refresh-ifs/',
        views.refresh_master_data_from_ifs,
        name='refresh_master_data_from_ifs',
    ),
    path(
        'admin-control/employee-active/',
        views.set_employee_active,
        name='set_employee_active',
    ),
    path(
        'admin-control/mapping-save/',
        views.save_activity_mapping,
        name='save_activity_mapping',
    ),
    path('timesheet/', views.timesheet_register, name='timesheet_register'),
    path('timesheet/register/', views.timesheet_register, name='timesheet_register_page'),
    path('timesheet/ifs-employees/', views.ifs_employees, name='ifs_employees'),
    path('timesheet/ifs-projects/', views.ifs_projects, name='ifs_projects'),
    path(
        'timesheet/ifs-activity-codes/',
        views.ifs_activity_codes,
        name='ifs_activity_codes',
    ),
    path(
        'timesheet/employee-day-summary/',
        views.employee_day_summary,
        name='employee_day_summary',
    ),
    path('edit-records/', views.edit_time_records, name='edit_time_records'),
    path('edit-records/save/', views.save_time_record, name='save_time_record'),
    path(
        'edit-records/bulk-save/',
        views.bulk_save_time_records,
        name='bulk_save_time_records',
    ),
    path(
        'edit-records/send-to-ifs/',
        views.send_records_to_ifs,
        name='send_records_to_ifs',
    ),
    path('edit-records/create/', views.create_time_record, name='create_time_record'),
    path('edit-records/delete/', views.delete_time_record, name='delete_time_record'),
    path('edit-records/topup-preview/', views.topup_preview, name='topup_preview'),
    path('edit-records/topup-apply/', views.topup_apply, name='topup_apply'),
    path('stock-scanner/', views.stock_scanner, name='stock_scanner'),
    path(
        'stock-scanner/recent/',
        views.stock_scanner_recent,
        name='stock_scanner_recent',
    ),
    path(
        'stock-scanner/save/',
        views.stock_scanner_save,
        name='stock_scanner_save',
    ),
    path(
        'stock-scanner/delete/<int:scan_id>/',
        views.stock_scanner_delete,
        name='stock_scanner_delete',
    ),
]
