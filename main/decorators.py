import datetime
from django.shortcuts import redirect
from django.contrib import messages
from django.contrib.auth import logout

def critical_view_decorator(view_func):
    """
    Custom decorator to enforce re-authentication for critical views.
    """
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.warning(request, 'Please log in again.')
            return redirect('login')

        login_time = request.session.get('login_time')
        if login_time:
            login_datetime = datetime.datetime.fromisoformat(login_time)
            if (datetime.datetime.now() - login_datetime).total_seconds() > 1800:
                logout(request)
                messages.warning(request, 'Session expired. Please log in again.')
                return redirect('login')

        return view_func(request, *args, **kwargs)
    return wrapper
