from django.contrib.auth import logout
from django.shortcuts import redirect

class ForceReLoginMiddleware:
    """
    Logs out users immediately after one authenticated request.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            if not request.session.get('used_once', False):
                request.session['used_once'] = True  # Allow the current request
            else:
                logout(request)
                request.session.flush()
                return redirect('login')
        return self.get_response(request)
