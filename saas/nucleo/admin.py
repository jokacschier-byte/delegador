"""
Telas de configuracao (Django Admin) para cada cartorio-cliente.

Um usuario normal (nao-superuser) so ve e so edita os dados do SEU
proprio cartorio -- o campo "cartorio" fica escondido e e preenchido
automaticamente a partir do perfil do usuario logado. Um superuser (a
equipe que opera o SaaS) continua vendo tudo, de todos os cartorios.
"""

from django.contrib import admin

from .models import Cartorio, Escrevente, Grupo, Natureza, Perfil, Protocolo

admin.site.site_header = "Distribuidor de Protocolos"
admin.site.site_title = "Distribuidor de Protocolos"
admin.site.index_title = "Configurações"


def _cartorio_do_usuario(request):
    perfil = getattr(request.user, "perfil", None)
    return perfil.cartorio if perfil else None


class TenantScopedAdmin(admin.ModelAdmin):
    """ModelAdmin que isola os registros pelo cartorio do usuario logado."""

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        cartorio = _cartorio_do_usuario(request)
        return qs.filter(cartorio=cartorio) if cartorio else qs.none()

    def save_model(self, request, obj, form, change):
        if not request.user.is_superuser:
            obj.cartorio = _cartorio_do_usuario(request)
        super().save_model(request, obj, form, change)

    def get_exclude(self, request, obj=None):
        excluidos = list(super().get_exclude(request, obj) or [])
        if not request.user.is_superuser:
            excluidos.append("cartorio")
        return excluidos

    def _filtrar_por_cartorio(self, field, request):
        if request.user.is_superuser:
            return field
        cartorio = _cartorio_do_usuario(request)
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
    list_display = ("nome",)
    filter_horizontal = ("escreventes",)


@admin.register(Natureza)
class NaturezaAdmin(TenantScopedAdmin):
    list_display = ("nome", "grupo", "tempo_estimado_minutos")
    list_filter = ("grupo",)


@admin.register(Protocolo)
class ProtocoloAdmin(TenantScopedAdmin):
    list_display = ("numero", "natureza", "urgente", "escrevente_responsavel", "status", "criado_em")
    list_filter = ("status", "urgente", "natureza__grupo")
    readonly_fields = ("tempo_estimado_minutos",)


# Cartorio e Perfil so fazem sentido para quem administra o SaaS como um
# todo (a equipe interna), nao para o cliente final -- por isso ficam
# visiveis so para superuser (comportamento padrao do admin.site).
admin.site.register(Cartorio)
admin.site.register(Perfil)
