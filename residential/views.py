from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Fund,Residence
from .services.fund_service import get_fund_summary
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render
from django.db.models import Sum
from datetime import datetime


def download_fund_pdf(request):
    fund_id = request.GET.get("fund")
    if not fund_id:
        return HttpResponse("Fondo no seleccionado")

    from django.utils import timezone
    import calendar

    now = timezone.now()
    try:
        selected_year  = int(request.GET.get("year",  now.year))
        selected_month = int(request.GET.get("month", now.month))
    except (ValueError, TypeError):
        selected_year  = now.year
        selected_month = now.month

    fund = Fund.objects.get(id=fund_id)

    last_day = calendar.monthrange(selected_year, selected_month)[1]
    month_start = timezone.make_aware(datetime(selected_year, selected_month, 1, 0, 0, 0))
    month_end   = timezone.make_aware(datetime(selected_year, selected_month, last_day, 23, 59, 59))

    payments_in_month     = fund.payments.filter(payment_date__gte=month_start, payment_date__lte=month_end)
    disbursements_in_month = fund.disbursements.filter(created_at__gte=month_start, created_at__lte=month_end).order_by('-created_at')

    summary          = get_fund_summary(fund, payments_qs=payments_in_month)
    total_aportes    = sum(item['total'] for item in summary)
    total_desembolsos = disbursements_in_month.aggregate(total=Sum('amount'))['total'] or 0

    is_current_month = (selected_year == now.year and selected_month == now.month)
    MONTHS_ES = {
        1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",
        7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"
    }

    if is_current_month:
        total_p = fund.payments.aggregate(total=Sum('amount'))['total'] or 0
        total_d = fund.disbursements.aggregate(total=Sum('amount'))['total'] or 0
        saldo_disponible = total_p - total_d
        saldo_label = "Saldo Actual"
    else:
        total_p = fund.payments.filter(payment_date__lte=month_end).aggregate(total=Sum('amount'))['total'] or 0
        total_d = fund.disbursements.filter(created_at__lte=month_end).aggregate(total=Sum('amount'))['total'] or 0
        saldo_disponible = total_p - total_d
        saldo_label = f"Saldo de Cierre ({MONTHS_ES[selected_month]} {selected_year})"

    html = render_to_string("pdf/fund_report.html", {
        "fund":             fund,
        "condominium":      fund.condominium,
        "summary":          summary,
        "total_aportes":    total_aportes,
        "total_desembolsos": total_desembolsos,
        "saldo_disponible": saldo_disponible,
        "saldo_label":      saldo_label,
        "disbursements":    disbursements_in_month,
        "selected_month":   MONTHS_ES[selected_month],
        "selected_year":    selected_year,
        "generated_at":     datetime.now(),
    })

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="reporte_fondo_{fund.id}_{selected_year}_{selected_month:02d}.pdf"'
    pisa.CreatePDF(html, dest=response)
    return response

def get_residences_by_fund(request):
    fund_id = request.GET.get("fund_id")

    if not fund_id:
        return JsonResponse([], safe=False)

    try:
        fund = Fund.objects.get(id=fund_id)

        residences = Residence.objects.filter(
            condominium=fund.condominium
        )

        data = [
            {
                'id': r.id,
                'name': f"{r.identifier} - {r.owner_name}"
            }
            for r in residences
        ]
        return JsonResponse(data, safe=False)

    except Fund.DoesNotExist:
        return JsonResponse([], safe=False)

def landing(request):
    context = {
        "spots_left": 3
    }
    return render(request, "landing.html", context)