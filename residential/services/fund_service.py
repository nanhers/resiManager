from django.db.models import Sum
from residential.models import Payment

def get_fund_summary(fund, payments_qs=None):
    if payments_qs is None:
        payments_qs = Payment.objects.filter(fund=fund)
    
    return (
        payments_qs
        .values('residence__identifier', 'residence__owner_name')
        .annotate(total=Sum('amount'))
        .order_by('residence__identifier')
    )