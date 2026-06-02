from urllib import response

from django import forms
from django.contrib import admin
from .models import Condominium, Residence, Fund, Payment, FundSummaryProxy, Disbursement
from residential import models
from django.db.models import Sum
from django.utils.html import format_html
from .services.fund_service import get_fund_summary
from django.template.response import TemplateResponse
from django.utils import timezone
import calendar

# Register your models here.
class PaymentAdminForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance and self.instance.pk and self.instance.fund_id:
            fund = self.instance.fund
            self.fields['residence'].queryset = Residence.objects.filter(
                condominium=fund.condominium
            )
        elif 'fund' in (self.data or {}):
            try:
                fund_id = int(self.data.get('fund'))
                fund = Fund.objects.get(pk=fund_id)
                self.fields['residence'].queryset = Residence.objects.filter(
                    condominium=fund.condominium
                )
            except (ValueError, TypeError, Fund.DoesNotExist):
                self.fields['residence'].queryset = Residence.objects.none()
        else:
            self.fields['residence'].queryset = Residence.objects.none()

class ResidenceInline(admin.TabularInline):
    model = Residence
    extra = 1

@admin.register(Condominium)
class CondominiumAdmin(admin.ModelAdmin):
    list_display = ('name', 'city', 'state', 'total_residences', 'created_by')
    inlines = [ResidenceInline]

    def total_residences(self, obj):
        return obj.residences.count()
    total_residences.short_description = 'Total Residencias'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

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
        total_aportes = obj.payments.aggregate(total=Sum('amount'))['total'] or 0
        total_desembolsos = obj.disbursements.aggregate(total=Sum('amount'))['total'] or 0
        saldo = total_aportes - total_desembolsos
        color = "red" if saldo < 0 else "green"

        html = "<table style='width:100%; border-collapse: collapse;'>"
        html += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>Total Aportes</td><td style='border: 1px solid #ddd; padding: 8px;'>${total_aportes:,.2f}</td></tr>"
        html += f"<tr><td style='border: 1px solid #ddd; padding: 8px;'>Total Desembolsos</td><td style='border: 1px solid #ddd; padding: 8px;'>${total_desembolsos:,.2f}</td></tr>"
        html += f"<tr><td style='border: 1px solid #ddd; padding: 8px; font-weight:bold;'>Saldo Disponible</td><td style='border: 1px solid #ddd; padding: 8px; font-weight:bold; color:{color};'>${saldo:,.2f}</td></tr>"
        html += "</table>"

        return format_html(html)
    payment_summary.short_description = 'Resumen de Pagos'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    form = PaymentAdminForm
    list_display = ('get_identifier', 'get_owner', 'amount', 'get_condominium')

    list_filter = ('fund__condominium',)

    search_fields = ('residence__owner_name', 'residence__identifier')

    class Media:
        js = ('js/payment_filter.js',)

    def get_identifier(self, obj):
        try:
            return obj.residence.identifier
        except Residence.DoesNotExist:
            return "N/A"
        
    get_identifier.short_description = 'Identificador'

    def get_owner(self, obj):
        try:
            return obj.residence.owner_name
        except Residence.DoesNotExist:
            return "N/A"        
        
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
        now = timezone.now()

        selected_fund = request.GET.get("fund")
        selected_year  = request.GET.get("year",  str(now.year))
        selected_month = request.GET.get("month", str(now.month))

        try:
            selected_year  = int(selected_year)
            selected_month = int(selected_month)
        except (ValueError, TypeError):
            selected_year  = now.year
            selected_month = now.month

        all_funds = (
            Fund.objects
            .select_related('condominium')
            .order_by('condominium__name', 'name')
        )

        payment_years     = Payment.objects.dates('payment_date', 'year')
        disbursement_years = Disbursement.objects.dates('created_at', 'year')
        year_set = {now.year}
        for d in payment_years:
            year_set.add(d.year)
        for d in disbursement_years:
            year_set.add(d.year)
        available_years = sorted(year_set, reverse=True)

        MONTHS_ES = {
            1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
            5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
            9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
        }
        available_months = [(n, MONTHS_ES[n]) for n in range(1, 13)]

        summary            = []
        total_aportes      = 0
        total_desembolsos  = 0
        saldo_disponible   = 0
        disbursements      = []
        is_current_month   = False
        saldo_label        = "Saldo Disponible"

        if selected_fund:
            try:
                fund = Fund.objects.get(id=selected_fund)

                last_day = calendar.monthrange(selected_year, selected_month)[1]
                from datetime import date, datetime
                month_start = timezone.make_aware(
                    datetime(selected_year, selected_month, 1, 0, 0, 0)
                )
                month_end = timezone.make_aware(
                    datetime(selected_year, selected_month, last_day, 23, 59, 59)
                )

                is_current_month = (
                    selected_year  == now.year and
                    selected_month == now.month
                )

                payments_in_month = fund.payments.filter(
                    payment_date__gte=month_start,
                    payment_date__lte=month_end,
                )
                summary       = get_fund_summary(fund, payments_qs=payments_in_month)
                total_aportes = sum(item['total'] for item in summary)

                disbursements_in_month = fund.disbursements.filter(
                    created_at__gte=month_start,
                    created_at__lte=month_end,
                ).order_by('-created_at')
                total_desembolsos = (
                    disbursements_in_month.aggregate(total=Sum('amount'))['total'] or 0
                )
                disbursements = disbursements_in_month

                if is_current_month:
                    total_p_acum = fund.payments.aggregate(total=Sum('amount'))['total'] or 0
                    total_d_acum = fund.disbursements.aggregate(total=Sum('amount'))['total'] or 0
                    saldo_disponible = total_p_acum - total_d_acum
                    saldo_label = "Saldo Actual"
                else:
                    total_p_hasta = (
                        fund.payments
                        .filter(payment_date__lte=month_end)
                        .aggregate(total=Sum('amount'))['total'] or 0
                    )
                    total_d_hasta = (
                        fund.disbursements
                        .filter(created_at__lte=month_end)
                        .aggregate(total=Sum('amount'))['total'] or 0
                    )
                    saldo_disponible = total_p_hasta - total_d_hasta
                    saldo_label = f"Saldo de Cierre ({MONTHS_ES[selected_month]} {selected_year})"

            except Fund.DoesNotExist:
                pass

        context = {
            **self.admin_site.each_context(request),
            "all_funds":        all_funds,
            "selected_fund":    selected_fund,
            "available_years":  available_years,
            "available_months": available_months,
            "selected_year":    selected_year,
            "selected_month":   selected_month,
            "is_current_month": is_current_month,
            "summary":           summary,
            "total_aportes":     total_aportes,
            "total_desembolsos": total_desembolsos,
            "saldo_disponible":  saldo_disponible,
            "saldo_label":       saldo_label,
            "disbursements":     disbursements,
        }

        return TemplateResponse(request, "admin/fund_summary_list.html", context)


@admin.register(Disbursement)
class DisbursementAdmin(admin.ModelAdmin):
    list_display = ('fund', 'get_condominium', 'amount', 'description', 'created_at')
    list_filter = ('fund__condominium', 'fund')
    search_fields = ('description', 'fund__name')
    readonly_fields = ('created_at',)

    def get_condominium(self, obj):
        return obj.fund.condominium.name
    get_condominium.short_description = 'Condominio'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('fund__condominium')