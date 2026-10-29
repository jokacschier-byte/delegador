"""
Telas de configuracao (Django Admin) para cada cartorio-cliente.

Um usuario normal (nao-superuser) so ve e so edita os dados do SEU
proprio cartorio -- o campo "cartorio" fica escondido e e preenchido
automaticamente a partir do perfil do usuario logado. Um superuser (a
equipe que opera o SaaS) continua vendo tudo, de todos os cartorios.
"""

from django.contrib import admin

from .models import Cartorio, Escrevente, Ferias, Grupo, Natureza, Perfil, Protocolo, cartorio_do_usuario

admin.site.site_header = "registrai"
admin.site.site_title = "registrai"
admin.site.index_title = "Configurações"


class TenantScopedAdmin(admin.ModelAdmin):
    """ModelAdmin que isola os registros pelo cartorio do usuario logado."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        cartorio = cartorio_do_usuario(request.user)
        return qs.filter(cartorio=cartorio) if cartorio else qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.cartorio = cartorio_do_usuario(request.user)
        super().save_model(request, obj, form, change)

    def get_exclude(self, request, obj=None):
        excluidos = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            excluidos.append("cartorio")
        return excluidos

    def _filtrar_por_cartorio(self, field, request):
        if request.user.is_superuser:
            return field
        cartorio = cartorio_do_usuario(request.user)
        if cartorio is not None and hasattr(field, "queryset") and hasattr(field.queryset.model, "cartorio_id"):
            field.queryset = field.queryset.filter(cartorio=cartorio)
        return field

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        field = super().formfield_for_foreignkey(db_field, request, **kwargs)
        return self._filtrar_por_cartorio(field, request)

    def formfield_for_manytomany(self, db_field, request, **kwargs):
        field = super().formfield_for_manytomany(db_field, request, **kwargs)
        return self._filtrar_por_cartorio(field, request)


@admin.register(Escrevente)
class EscreventeAdmin(TenantScopedAdmin):
    list_display = ("nome", "ativo")
    list_filter = ("ativo",)


@admin.register(Grupo)
class GrupoAdmin(TenantScopedAdmin):
    list_display = ("nome", "peso_extra_matricula_dias", "peso_extra_parte_dias")
    filter_horizontal = ("escreventes",)


@admin.register(Natureza)
class NaturezaAdmin(TenantScopedAdmin):
    list_display = ("nome", "grupo", "peso_base_dias", "grupo_se_inventario", "amostras")
    list_filter = ("grupo",)
    readonly_fields = ("amostras",)


@admin.register(Protocolo)
class ProtocoloAdmin(TenantScopedAdmin):
    list_display = (
        "numero", "natureza", "urgente", "escrevente_responsavel", "status", "tipo", "peso_dias", "criado_em",
    )
    list_filter = ("status", "tipo", "urgente", "natureza__grupo")
    readonly_fields = ("peso_dias",)


@admin.register(Ferias)
class FeriasAdmin(TenantScopedAdmin):
    list_display = ("escrevente", "inicio", "fim")
    list_filter = ("escrevente",)


# Cartorio e Perfil so fazem sentido para quem administra o SaaS como um
# todo (a equipe interna), nao para o cliente final -- por isso ficam
# visiveis so para superuser (comportamento padrao do admin.site).
admin.site.register(Cartorio)
admin.site.register(Perfil)
