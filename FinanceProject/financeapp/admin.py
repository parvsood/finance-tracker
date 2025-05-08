from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import UserProfile, Transaction, ContactSubmission

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'UserProfile'

class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline,)

class TransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'category', 'date', 'payment_method', 'transaction_type')
    list_filter = ('category', 'payment_method', 'transaction_type', 'date')
    search_fields = ('category', 'description', 'user__username')
    date_hierarchy = 'date'

class ContactSubmissionAdmin(admin.ModelAdmin):
    list_display = ('first_name', 'last_name', 'email', 'phone', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('first_name', 'last_name', 'email', 'message')
    readonly_fields = ('created_at',)
    date_hierarchy = 'created_at'

admin.site.unregister(User)
admin.site.register(User, UserAdmin)
admin.site.register(Transaction, TransactionAdmin)
admin.site.register(ContactSubmission, ContactSubmissionAdmin)
