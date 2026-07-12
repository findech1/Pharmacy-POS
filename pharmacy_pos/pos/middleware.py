from django.contrib.auth import logout
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone

SESSION_TIMEOUT_SECONDS = 15 * 60  # 15 minutes, per SRS Section 5.3


class ActiveBranchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            profile = getattr(request.user, 'profile', None)
            if profile:
                is_admin = profile.role == 'admin'
                request.is_branch_admin = is_admin

                if 'active_branch_id' in request.session:
                    stored = request.session['active_branch_id']
                    if stored is None and is_admin:
                        request.active_branch_id = None
                    elif stored and profile.get_accessible_branches().filter(id=stored).exists():
                        request.active_branch_id = stored
                    elif is_admin:
                        request.active_branch_id = None
                    else:
                        default_branch = profile.branch
                        request.active_branch_id = default_branch.id if default_branch else None
                else:
                    if is_admin:
                        request.active_branch_id = None
                    else:
                        default_branch = profile.branch
                        request.active_branch_id = default_branch.id if default_branch else None
                    request.session['active_branch_id'] = request.active_branch_id
            else:
                request.active_branch_id = None
                request.is_branch_admin = False
        return self.get_response(request)


class SessionTimeoutMiddleware:
    """
    REQ (SRS Section 5.3): automated terminal locks must activate after 15
    continuous minutes of operational inactivity. Any authenticated request
    updates 'last_activity'; if too much time has passed since the last one,
    the session is force-ended and the user is sent back to login.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            now = timezone.now().timestamp()
            last_activity = request.session.get('last_activity')

            if last_activity is not None and (now - last_activity) > SESSION_TIMEOUT_SECONDS:
                username = request.user.username
                from .audit import log_audit
                log_audit(request, 'logout', details=f'Session for {username} auto-expired after 15 minutes of inactivity.')
                logout(request)
                messages.warning(request, 'You were logged out after 15 minutes of inactivity. Please log in again.')
                return redirect('login')

            request.session['last_activity'] = now

        return self.get_response(request)