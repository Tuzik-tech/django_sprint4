from django.contrib import admin

from .models import Category, Location, Post, Comment


admin.site.empty_value_display = 'Не задано'


class PostInLine(admin.TabularInline):
    model = Post
    extra = 0


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('text', 'post', 'author', 'created_at')
    list_display_links = ('text',)
    search_fields = ('text',)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    inlines = (
        PostInLine,
    )


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    inlines = (
        PostInLine,
    )


@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'pub_date',
        'author',
        'location',
        'category',
        'is_published',
    )
    list_editable = (
        'is_published',
        'category',
    )
    search_fields = ('title',)
    list_display_links = ('title',)
