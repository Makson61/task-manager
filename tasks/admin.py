from django.contrib import admin

from .models import Category, Task


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'owner', 'tasks_count')
    list_filter = ('owner',)
    search_fields = ('name', 'owner__username')
    list_select_related = ('owner',)

    @admin.display(description='задач')
    def tasks_count(self, category):
        return category.tasks.count()


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'category', 'priority', 'due_date', 'completed', 'date_added')
    list_filter = ('completed', 'priority', 'due_date', 'owner', 'category')
    list_editable = ('completed',)
    search_fields = ('title', 'description', 'owner__username')
    list_select_related = ('owner', 'category')
    date_hierarchy = 'date_added'
    readonly_fields = ('date_added', 'completed_at')
    fieldsets = (
        (None, {'fields': ('owner', 'title', 'description')}),
        ('Планирование', {'fields': ('due_date', 'priority', 'category')}),
        ('Состояние', {'fields': ('completed', 'completed_at', 'date_added')}),
    )
