"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from residential.views import download_fund_pdf
from django.urls import path
from residential.views import get_residences_by_fund, landing

urlpatterns = [
    path('admin/', admin.site.urls),
    path('fund-report-pdf/', download_fund_pdf, name='fund_report_pdf'),
    path('get-residences/', get_residences_by_fund, name='get_residences'),
    path('', landing, name='landing'),
]
