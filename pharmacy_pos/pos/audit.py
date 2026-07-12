from .models import AuditLog


def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


def log_audit(request, action, obj=None, details='', model_name=None, object_id=None, object_repr=None):
    """
    Records a single unalterable audit entry.

    - request: the current HttpRequest (used for user, active branch, IP)
    - action: one of AuditLog.ACTION_CHOICES
    - obj: an optional model instance; if given, model_name/object_id/object_repr are
           derived from it automatically unless explicitly overridden
    - details: free-text note (e.g. "Sale total: Ksh 1200.00")
    """
    user = getattr(request, 'user', None)
    if user is not None and not user.is_authenticated:
        user = None

    branch_id = getattr(request, 'active_branch_id', None)

    if obj is not None:
        model_name = model_name or obj.__class__.__name__
        object_id = object_id or str(getattr(obj, 'pk', ''))
        object_repr = object_repr or str(obj)[:255]

    AuditLog.objects.create(
        user=user,
        branch_id=branch_id,
        action=action,
        model_name=model_name or '',
        object_id=object_id or '',
        object_repr=object_repr or '',
        details=details,
        ip_address=get_client_ip(request),
    )
    