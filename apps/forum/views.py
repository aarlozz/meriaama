from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from .models import ForumPost
from .forms import ForumPostForm, ForumCommentForm


@login_required
def forum_list_page(request):
    """GET /forum/?stage=second_trimester -- browse approved posts, optionally filtered."""
    posts = ForumPost.objects.filter(is_approved=True)
    stage = request.GET.get("stage", "")
    if stage:
        posts = posts.filter(stage=stage)

    return render(request, "forum/list.html", {
        "posts": posts,
        "stages": ForumPost.Stage.choices,
        "selected_stage": stage,
    })


@login_required
def forum_create_page(request):
    """GET/POST /forum/new/ -- start a new post."""
    if request.method == "POST":
        form = ForumPostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.author = request.user
            post.save()
            return redirect("forum-detail", post_id=post.id)
    else:
        form = ForumPostForm()

    return render(request, "forum/create.html", {"form": form})


@login_required
def forum_detail_page(request, post_id):
    """GET/POST /forum/<id>/ -- read a post, add a comment."""
    post = get_object_or_404(ForumPost, id=post_id, is_approved=True)

    if request.method == "POST":
        form = ForumCommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.post = post
            comment.author = request.user
            comment.save()
            return redirect("forum-detail", post_id=post.id)
    else:
        form = ForumCommentForm()

    return render(request, "forum/detail.html", {"post": post, "form": form})