from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect

from .forms import PostForm, CommentForm
from .models import Post, Group, User, Follow

from django.conf import settings


def paginator(request, posts_list):
    paginator = Paginator(posts_list, settings.SLICE_POSTS)
    page_number = request.GET.get('page', 1)
    page_obj = paginator.get_page(page_number)
    return page_obj


def index(request):
    """Главная страница"""
    template = 'posts/index.html'
    posts_list = Post.objects.select_related('author', 'group')
    page_obj = paginator(request, posts_list)
    context = {
        'page_obj': page_obj,
    }
    return render(request, template, context)


def group_posts(request, slug):
    """Группы постов"""
    template = 'posts/group_list.html'
    group = get_object_or_404(Group, slug=slug)
    posts_list = group.posts.select_related('author', 'group')
    page_obj = paginator(request, posts_list)
    context = {
        'group': group,
        'page_obj': page_obj,
    }
    return render(request, template, context)


def profile(request, username):
    user = get_object_or_404(User, username=username)
    posts_list = user.posts.select_related('group')

    following = (request.user.is_authenticated
                 and user.following.filter(author=user, user=request.user
                                           ).exists())
    page_obj = paginator(request, posts_list)
    context = {
        'author': user,
        'page_obj': page_obj,
        'posts_total': page_obj.paginator.count,
        'following': following,
    }
    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    posts_total = post.author.posts.count()

    comments = post.comments.all()

    context = {
        'post': post,
        'posts_total': posts_total,
        'form': CommentForm(),
        'comments': comments,
    }
    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):

    form = PostForm(
        request.POST or None,
        files=request.FILES or None
    )

    if form.is_valid():
        post = form.save(commit=False)
        post.author = request.user
        post.save()
        return redirect(
            'posts:profile', request.user
        )

    context = {
        'form': form,
        'is_edit': False,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def post_edit(request, post_id):
    """Редактирование поста"""
    post = get_object_or_404(Post, pk=post_id)

    if request.user != post.author:
        return redirect(
            'posts:post_detail', post_id
        )

    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post
    )

    if form.is_valid():
        form.save()
        return redirect(
            'posts:post_detail', post_id
        )

    context = {
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/create_post.html', context)


@login_required
def add_comment(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    user = get_object_or_404(User, username=request.user)
    posts = Post.objects.filter(author__following__user=user).all()
    page_obj = paginator(request, posts)
    context = {
        'page_obj': page_obj,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    follow = Follow.objects.filter(user=request.user, author=author).exists()
    if not follow and username != request.user.username:
        Follow.objects.create(user=request.user, author=author)
    return redirect('posts:follow_index')


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect('posts:follow_index')
