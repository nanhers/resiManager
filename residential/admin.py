from urllib import response

from django.contrib import admin
from .models import Condominium, Residence, Fund, Payment, FundSummaryProxy
from residential import models
from django.db.models import Sum
from django.utils.html import format_html
from .services.fund_service import get_fund_summary
from django.template.response import TemplateResponse

# Register your models here.
class ResidenceInline(admin.TabularInline):
    model = Residence
    extra = 1

@admin.register(Condominium)
class CondominiumAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'total_residences')
    inlines = [ResidenceInline]

    def total_residences(self, obj):
        return obj.residences.count()
    total_residences.short_description = 'Total Residencias'

@admin.register(Residence)
class ResidenceAdmin(admin.ModelAdmin):
    list_display = ('identifier', 'owner_name', 'get_condominium')
    list_filter = ('condominium',)
    search_fields = ('identifier', 'owner_name')

    def get_condominium(self, obj):
        return obj.condominium.name

    get_condominium.short_description = 'Condominio'

@admin.register(Fund)
class FundAdmin(admin.ModelAdmin):
    list_display = ('name', 'condominium', 'is_active', 'created_at')
    list_filter = ('condominium', 'is_active')
    search_fields = ('name', 'description')

    readonly_fields = ('payment_summary',)

    fields = ('condominium', 'name', 'description', 'is_active', 'payment_summary')

    def payment_summary(self, obj):
        data = get_fund_summary(obj)

        if not data:
            return "No hay pagos registrados para este fondo."

        html = "<h3>Aportes por Residencia</h3>"
        html += "<table style='width:100%; border-collapse: collapse;'>"
        html += "<tr><th style='border: 1px solid #ddd; padding: 8px;'>Residencia</th><th style='border: 1px solid #ddd; padding: 8px;'>Total Aportado</th></tr>"

        total_amount = 0

        for item in data:
            total_amount += item['total']
            html += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>{item['residence__identifier']}</td><td style='border: 1px solid #ddd; padding: 8px;'>${item['total']:.2f}</td></tr>"

        html += f"<tr><td style='border: 1px solid #ddd; padding: 8px; font-weight: bold;'>Total General</td><td style='border: 1px solid #ddd; padding: 8px; font-weight: bold;'>${total_amount:.2f}</td></tr>"
        html += "</table>"

        return format_html(html)
    payment_summary.short_description = 'Resumen de Pagos'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('get_identifier', 'get_owner', 'amount', 'get_condominium')

    list_filter = ('fund__condominium',)

    search_fields = ('residence__owner_name', 'residence__identifier')

    class Media:
        js = ('js/payment_filter.js',)

    def get_identifier(self, obj):
        return obj.residence.identifier
    get_identifier.short_description = 'Identificador'

    def get_owner(self, obj):
        return obj.residence.owner_name
    get_owner.short_description = 'Propietario'

    def get_condominium(self, obj):
        return obj.fund.condominium.name
    get_condominium.short_description = 'Condominio'


@admin.register(FundSummaryProxy)
class FundSummaryAdmin(admin.ModelAdmin):
    change_list_template = "admin/fund_summary_list.html"

    def has_add_permission(self, request):
        return False

    def changelist_view(self, request, extra_context=None):
        condominiums = Condominium.objects.all()

        selected_condo = request.GET.get("condominium")
        selected_fund = request.GET.get("fund")

        funds = Fund.objects.filter(condominium_id=selected_condo) if selected_condo else []

        summary = []
        total_general = 0

        if selected_condo and selected_fund:
            fund = Fund.objects.get(id=selected_fund)
            summary = get_fund_summary(fund)
            total_general = sum(item['total'] for item in summary)

        context = {
            **self.admin_site.each_context(request),
            "condominiums": condominiums,
            "funds": funds,
            "selected_condo": selected_condo,
            "selected_fund": selected_fund,
            "summary": summary,
            "total_general": total_general,
        }

        return TemplateResponse(request, "admin/fund_summary_list.html", context)