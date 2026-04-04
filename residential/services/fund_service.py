from django.db.models import Sum
from residential.models import Payment

def get_fund_summary(fund):
    return (
        Payment.objects
        .filter(fund=fund)
        .values('residence__identifier', 'residence__owner_name')
        .annotate(total=Sum('amount'))
        .order_by('residence__identifier')
    )