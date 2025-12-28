from django.utils import timezone
from django.contrib.auth import get_user_model
from django.views.generic import (
    DetailView, CreateView, ListView, UpdateView, DeleteView
)
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import Http404
from django.core.exceptions import PermissionDenied

from django.db.models import Count
from blog.models import Post, Category, Comment
from .forms import UserUpdateForm, PostForm, CommentForm

User = get_user_model()


def get_annotated_posts(queryset=None, published_only=True):
    """
    Возвращает QuerySet с аннотированным количеством комментариев.
    Если published_only=True — применяет фильтрацию по публикации.
    Если queryset не передан — использует Post.objects.all().
    """
    if queryset is None:
        queryset = Post.objects.all()

    queryset = queryset.select_related(
        'author', 'category', 'location'
    ).annotate(
        comment_count=Count('comments')
    )

    if published_only:
        queryset = queryset.filter(
            is_published=True,
            category__is_published=True,
            pub_date__lte=timezone.now()
        )

    return queryset.order_by(*Post._meta.ordering)


class PostsListView(ListView):
    model = Post
    template_name = 'blog/index.html'
    paginate_by = 10

    def get_queryset(self):
        return get_annotated_posts()  # по умолчанию — только опубликованные


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'
    pk_url_kwarg = 'post_id'

    def get_object(self, queryset=None):
        post = super().get_object(queryset)

        # Автор видит ВСЕ свои посты (включая снятые с публикации)
        if (self.request.user.is_authenticated
                and self.request.user == post.author):
            return post

        if (post.is_published
                and post.category.is_published
                and post.pub_date <= timezone.now()):
            return post

        # Если условия не выполнены - пост не найден (404)
        raise Http404("Пост не найден")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = CommentForm()
        context['comments'] = (
            self.object.comments.select_related('author')
        )
        return context


def category_posts(request, category_slug):
    template = "blog/category.html"

    category = get_object_or_404(
        Category,
        slug=category_slug,
        is_published=True
    )

    # Используем вашу функцию — она уже аннотирует comment_count
    posts = get_annotated_posts(
        queryset=category.posts.all(),
        published_only=True
    )

    paginator = Paginator(posts, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'category': category  # на случай, если нужен заголовок категории
    }
    return render(request, template, context)


class ProfileView(DetailView):
    model = User
    template_name = 'blog/profile.html'
    context_object_name = 'profile'
    slug_field = 'username'
    slug_url_kwarg = 'username'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_user = self.request.user
        
        if current_user.is_authenticated and current_user == self.object:
            # Автор видит все свои посты — без фильтрации по публикации
            posts = get_annotated_posts(
                queryset=Post.objects.filter(author=self.object),
                published_only=False
            )
        else:
            # Гости — только опубликованные
            posts = get_annotated_posts(
                queryset=Post.objects.filter(author=self.object),
                published_only=True
            )

        paginator = Paginator(posts, 10)
        page_number = self.request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        context['page_obj'] = page_obj
        return context


class ProfileUpdateView(LoginRequiredMixin, UpdateView):
    model = User
    form_class = UserUpdateForm
    template_name = 'blog/user.html'

    def get_object(self, queryset=None):
        # Возвращаем текущего пользователя
        return self.request.user

    def get_success_url(self):
        # После успешного редактирования возвращаем на профиль
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )


class PostCreateView(LoginRequiredMixin, CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile',
            kwargs={'username': self.request.user.username}
        )

    def form_valid(self, form):
        form.instance.author = self.request.user

        # Если дата публикации не указана, ставим текущую
        if not form.instance.pub_date:
            form.instance.pub_date = timezone.now()

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание новой публикации'
        return context


class EditMixin(LoginRequiredMixin, UserPassesTestMixin):
    def test_func(self):
        post = self.get_object()
        return self.request.user == post.author

    def handle_no_permission(self):
        return redirect('blog:post_detail', post_id=self.kwargs.get('post_id'))


class PostUpdateView(EditMixin, UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:index')


class PostDeleteView(EditMixin, DeleteView):
    model = Post
    template_name = 'blog/create.html'
    pk_url_kwarg = 'post_id'
    success_url = reverse_lazy('blog:index')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = PostForm(instance=self.object)
        return context


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, id=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()

    return redirect('blog:post_detail', post_id=post_id)


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        comment = self.get_object()
        if comment.author != request.user:
            raise PermissionDenied("Вы не являетесь автором этого комментария")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        messages.success(self.request, 'Комментарий обновлен')
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail',
            kwargs={'post_id': self.object.post.id}
        )


class CommentDeleteView(EditMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def get_success_url(self):
        post_id = self.object.post.id
        return reverse_lazy('blog:post_detail', kwargs={'post_id': post_id})
