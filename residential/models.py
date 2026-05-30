from django.db import models
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator


class Condominium(models.Model):
    name = models.CharField("Nombre",max_length=50, validators=[MinLengthValidator(3)])
    country = models.CharField("País",max_length=50, validators=[MinLengthValidator(3)]) 
    city = models.CharField("Ciudad",max_length=100, validators=[MinLengthValidator(3)]) 
    state = models.CharField("Estado",max_length=100, blank=True, null=True)
    address = models.CharField("Dirección",max_length=250, validators=[MinLengthValidator(5)])
    zip_code = models.CharField("Código Postal",max_length=20, blank=True, null=True)

    class Meta:
        verbose_name = "Condominio"
        verbose_name_plural = "Condominios"

    def __str__(self):
        return self.name

class Residence(models.Model):
    condominium = models.ForeignKey(Condominium, on_delete=models.CASCADE, related_name='residences')
    identifier = models.CharField("Identificador",max_length=50)
    owner_name = models.CharField("Nombre del Propietario",max_length=255)
    owner_email = models.EmailField("Correo",blank=True, null=True)
    owner_phone = models.CharField("Teléfono",max_length=20, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Residencia"
        verbose_name_plural = "Residencias"
        ordering = ['identifier']
        constraints = [
            models.UniqueConstraint(fields=['condominium', 'identifier'], name='unique_residence_identifier')]
    

    def __str__(self):
        return f"{self.identifier} - {self.owner_name}"

class Fund(models.Model):
    condominium = models.ForeignKey(Condominium, on_delete=models.CASCADE, related_name='funds', verbose_name="Condominio")
    name = models.CharField("Nombre", max_length=255)
    description = models.TextField("Descripción", blank=True, null=True)
    is_active = models.BooleanField("Activo", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Fondo"
        verbose_name_plural = "Fondos"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.condominium.name} - {self.name}"
    
class Payment(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='payments', verbose_name="Fondo")
    residence = models.ForeignKey(Residence, on_delete=models.CASCADE)
    amount = models.DecimalField("Monto", max_digits=10, decimal_places=2)
    payment_date = models.DateTimeField("Fecha de Pago", auto_now_add=True)
    note = models.TextField("Nota")

    class Meta:
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"
        ordering = ['-payment_date']
       
    def clean(self):
        if not self.residence_id or not self.fund_id:
            return
        if  self.amount == 0:
            raise ValidationError({"amount": "El monto debe ser un valor diferente de cero."})
        if self.residence.condominium != self.fund.condominium:
            raise ValidationError("La residencia y el fondo deben pertenecer al mismo condominio.")
    
    def __str__(self):
        return f"Pago de {self.amount} por {self.residence.identifier} al fondo {self.fund.name}"

class FundSummaryProxy(Fund):
    class Meta:
        proxy = True
        verbose_name = "Resumen de aportes"
        verbose_name_plural = "Resumen de aportes"

class Disbursement(models.Model):
    fund = models.ForeignKey(Fund, on_delete=models.CASCADE, related_name='disbursements', verbose_name="Fondo")
    amount = models.DecimalField("Monto", max_digits=10, decimal_places=2)
    description = models.TextField("Descripción")
    created_at = models.DateTimeField("Fecha de Desembolso", auto_now_add=True)

    class Meta:
        verbose_name = "Desembolso"
        verbose_name_plural = "Desembolsos"
        ordering = ['-created_at']
    
    def clean(self):
        if self.amount is not None and self.amount <= 0:
            raise ValidationError({"amount": "La cantidad debe ser un valor positivo."})
    
        if self.fund_id and self.amount is not None:
            from django.db.models import Sum

            total_pagos = self.fund.payments.aggregate(total=Sum('amount'))['total'] or 0
        
        
            total_desembolsos = self.fund.disbursements.exclude(pk=self.pk).aggregate(total=Sum('amount'))['total'] or 0
        
            saldo = total_pagos - total_desembolsos

            if self.amount > saldo:
                raise ValidationError({
                    "amount": f"El monto excede el saldo disponible del fondo. Saldo actual: ${saldo:.2f}"
                })
        
    def save(self, *args, **kwargs):
        if self.amount is not None:
            self.amount = abs(self.amount)
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Desembolso de {self.amount} del fondo {self.fund.name}"