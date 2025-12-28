from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserChangeForm

from django import forms
from .models import Post, Category, Location, Comment

User = get_user_model()


class UserUpdateForm(UserChangeForm):
    """Форма для редактирования профиля пользователя."""

    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email', 'username')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Убираем поле пароля из формы
        self.fields.pop('password', None)


class PostForm(forms.ModelForm):
    """Форма для создания и редактирования поста."""

    class Meta:
        model = Post
        exclude = ['author']
        widgets = {
            'pub_date': forms.DateTimeInput(
                attrs={
                    'type': 'datetime-local',
                    'class': 'form-control',
                },
                format='%Y-%m-%dT%H:%M'  # Формат для HTML5
            ),
            'text': forms.Textarea(attrs={'rows': 10}),
        }
        help_texts = {
            'pub_date':
                '''Если установить дату в будущем
                — можно делать отложенные публикации.''',
            'is_published': 'Снимите галочку, чтобы скрыть публикацию.',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Ограничиваем категории только опубликованными
        self.fields['category'].queryset = Category.objects.filter(
            is_published=True
        ).only('title')

        # Ограничиваем локации только опубликованными
        self.fields['location'].queryset = Location.objects.filter(
            is_published=True
        ).only('name')

        # Устанавливаем формат даты для виджета
        if self.instance.pk and self.instance.pub_date:
            self.initial['pub_date'] = self.instance.pub_date.strftime(
                '%Y-%m-%dT%H:%M')


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ('text',)
