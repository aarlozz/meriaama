from functools import wraps
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseForbidden


def data_entry_or_admin_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if not (request.user.role == "data_entry" or request.user.is_hospital_admin()):
            return HttpResponseForbidden("This page is for data entry staff only.")
        return view_func(request, *args, **kwargs)
    return wrapper


def doctor_required(view_func):
    @wraps(view_func)
    @login_required
    def wrapper(request, *args, **kwargs):
        if request.user.role != "doctor":
            return HttpResponseForbidden("This page is for doctors only.")
        return view_func(request, *args, **kwargs)
    return wrapper