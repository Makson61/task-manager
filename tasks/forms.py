from django import forms

from .models import Category, Task


class TaskForm(forms.ModelForm):
    """Поля задачи, доступные пользователю.

    Владелец и дата создания в форму не входят: их задаёт представление.
    Список категорий ограничен категориями этого же пользователя, иначе чужую
    категорию можно было бы подставить в POST-запросе.
    """

    class Meta:
        model = Task
        fields = ['title', 'description', 'due_date', 'priority', 'category', 'completed']
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Например: сдать отчёт по практике'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Подробности, шаги, ссылки'}),
            # Стандартный выбор даты и времени браузера, удобный и на телефоне.
            'due_date': forms.DateTimeInput(attrs={'type': 'datetime-local'}, format='%Y-%m-%dT%H:%M'),
            'priority': forms.RadioSelect,
        }
        help_texts = {'due_date': 'Можно не указывать. Просроченные задачи выделяются в списке.'}
        error_messages = {'due_date': {'invalid': 'Дата и время нужны в формате ДД.ММ.ГГГГ ЧЧ:ММ.'}}

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['category'].queryset = Category.objects.filter(owner=owner)
        self.fields['category'].empty_label = 'Без категории'


class CategoryForm(forms.ModelForm):
    """Новая категория. Проверяет, что такой у пользователя ещё нет."""

    class Meta:
        model = Category
        fields = ['name']
        labels = {'name': 'Название категории'}
        widgets = {'name': forms.TextInput(attrs={'placeholder': 'Учёба, дом, работа...'})}

    def __init__(self, *args, owner=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.owner = owner

    def clean_name(self):
        name = self.cleaned_data['name'].strip()
        if self.owner is not None and Category.objects.filter(owner=self.owner, name__iexact=name).exists():
            raise forms.ValidationError('Такая категория у вас уже есть.')
        return name
