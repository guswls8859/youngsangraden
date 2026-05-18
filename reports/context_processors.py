from .models import VacationRequest


def vacation_pending_count(request):
    """관리자에게만 대기 중인 휴가 신청 수를 컨텍스트로 제공."""
    if (
        not request.user.is_authenticated
        or getattr(request.user, 'organization', None) != 'operations'
        or getattr(request.user, 'role', None) != 'manager'
    ):
        return {}
    count = VacationRequest.objects.filter(status='pending').count()
    return {'pending_vacation_count': count}
