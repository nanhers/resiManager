from django.http import HttpResponse
from django.template.loader import render_to_string
from xhtml2pdf import pisa  # 👈 AQUÍ
from .models import Fund
from .services.fund_service import get_fund_summary
from datetime import datetime


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