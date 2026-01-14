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
    path('employee/<str:employee_id>/', views.timer_page, name='timer_page'),
    path('employee/<str:employee_id>/start/', views.start_timer, name='start_timer'),
    path('employee/<str:employee_id>/stop/', views.stop_timer, name='stop_timer'),
    path('admin-dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-dashboard/sync/', views.sync_to_excel, name='sync_to_excel'),
    path('admin-dashboard/export/', views.export_to_excel, name='export_to_excel'),
    path('admin-control/', views.admin_control_panel, name='admin_control_panel'),
    path('admin-control/save/', views.save_master_data, name='save_master_data'),
    path('edit-records/', views.edit_time_records, name='edit_time_records'),
    path('edit-records/save/', views.save_time_record, name='save_time_record'),
    path('edit-records/bulk-save/', views.bulk_save_time_records, name='bulk_save_time_records'),
    path('edit-records/create/', views.create_time_record, name='create_time_record'),
    path('edit-records/delete/', views.delete_time_record, name='delete_time_record'),
]
