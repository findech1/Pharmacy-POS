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