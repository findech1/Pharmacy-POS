from .models import Branch


def branch_context(request):
    if not request.user.is_authenticated:
        return {}
    return {
        'branches': Branch.objects.filter(is_active=True) if getattr(request, 'is_branch_admin', False) else [],
        'active_branch': Branch.objects.filter(id=request.active_branch_id).first() if getattr(request, 'active_branch_id', None) else None,
    }
    