from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User, Group

# Register your models here.

# Unregister the default User admin and register our custom one
admin.site.unregister(User)


# Customize User admin to make it easier to manage users with groups
@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Customized User admin for managing login accounts.

    Users are assigned to groups:
    - Admin group: Full access to all features including admin panels
    - Standard group: Access to regular features only (no admin access)
    """
    list_display = (
        'username', 'email', 'first_name', 'last_name',
        'get_groups', 'is_active', 'date_joined'
    )
    list_filter = ('groups', 'is_active', 'is_superuser', 'date_joined')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    filter_horizontal = ('groups', 'user_permissions')

    # Make groups more prominent in the form
    fieldsets = BaseUserAdmin.fieldsets
    fieldsets[1][1]['fields'] = ('first_name', 'last_name', 'email')

    def get_groups(self, obj):
        """Display user's groups"""
        groups = obj.groups.all()
        if groups:
            return ', '.join([group.name for group in groups])
        return 'No groups'
    get_groups.short_description = 'Groups'

    # Add helpful text
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj:  # Editing existing user
            form.base_fields['groups'].help_text = (
                'Select groups for this user. '
                'Admin group = full access, Standard group = regular access only.'
            )
        return form


# Unregister the default Group admin and register our custom one
admin.site.unregister(Group)

# Customize Group admin to show helpful information
@admin.register(Group)
class GroupAdmin(admin.ModelAdmin):
    """Customized Group admin"""
    list_display = ('name', 'get_user_count')
    search_fields = ('name',)

    def get_user_count(self, obj):
        """Display number of users in group"""
        return obj.user_set.count()
    get_user_count.short_description = 'Users'
