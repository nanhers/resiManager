from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa
from .models import Fund,Residence
from .services.fund_service import get_fund_summary
from datetime import datetime
from django.http import JsonResponse
from django.shortcuts import render


def download_fund_pdf(request):
    fund_id = request.GET.get("fund")

    if not fund_id:
        return HttpResponse("Fondo no seleccionado")

    fund = Fund.objects.get(id=fund_id)
    summary = get_fund_summary(fund)

    total_general = sum(item['total'] for item in summary)

    html = render_to_string("pdf/fund_report.html", {
        "fund": fund,
        "condominium": fund.condominium,
        "summary": summary,
        "total_general": total_general,
        "generated_at": datetime.now(),
    })

    response = HttpResponse(content_type="application/pdf")
    response['Content-Disposition'] = f'attachment; filename="reporte_fondo_{fund.id}.pdf"'

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