from django.urls import path

from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("protocolos/novo/", views.lancar_protocolo, name="lancar_protocolo"),
    path("historico/", views.historico, name="historico"),
    path("ferias/", views.ferias, name="ferias"),
    path("sincronizar/", views.sincronizar, name="sincronizar"),
]
