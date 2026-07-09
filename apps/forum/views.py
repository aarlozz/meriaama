from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Count, Q
from .models import ForumPost
from .forms import ForumPostForm, ForumCommentForm


@login_required
def forum_list_page(request):
    """GET /forum/?q=...&stage=...&sort=...&has_image=on -- browse + filter posts."""
    posts = ForumPost.objects.filter(is_approved=True).annotate(comment_count=Count("comments"))

    query = request.GET.get("q", "").strip()
    stage = request.GET.get("stage", "").strip()
    sort = request.GET.get("sort", "newest")
    has_image = request.GET.get("has_image") == "on"

    if query:
        posts = posts.filter(
            Q(title__icontains=query) | Q(body__icontains=query) | Q(author__username__icontains=query)
        )
    if stage:
        posts = posts.filter(stage=stage)
    if has_image:
        posts = posts.exclude(image="")

    sort_map = {
        "newest": "-created_at",
        "oldest": "created_at",
        "most_commented": "-comment_count",
    }
    posts = posts.order_by(sort_map.get(sort, "-created_at"))

    return render(request, "forum/list.html", {
        "posts": posts,
        "stages": ForumPost.Stage.choices,
        "selected_stage": stage,
        "query": query,
        "sort": sort,
        "has_image": has_image,
        "has_active_filters": bool(query or stage or has_image or sort != "newest"),
    })


@login_required
def forum_create_page(request):
    if request.method == "POST":
        form = ForumPostForm(request.POST, request.FILES)
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