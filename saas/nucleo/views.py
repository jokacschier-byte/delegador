"""
Views operacionais do dia a dia (nao sao telas de configuracao -- essas
ficam no Django Admin, ver admin.py).
"""

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import redirect, render

from . import distribuicao
from .models import Natureza, Protocolo


def _cartorio_do_usuario(request):
    return request.user.perfil.cartorio


class LancarProtocoloForm(forms.Form):
    numero = forms.CharField(label="Número do protocolo", max_length=50)
    natureza = forms.ModelChoiceField(label="Natureza", queryset=Natureza.objects.none())
    urgente = forms.BooleanField(label="Urgente", required=False)

    def __init__(self, *args, cartorio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["natureza"].queryset = Natureza.objects.filter(cartorio=cartorio).order_by("nome")


@login_required
def dashboard(request):
    cartorio = _cartorio_do_usuario(request)
    carga = distribuicao.carga_atual_minutos(cartorio)

    escreventes = []
    for escrevente in cartorio.escreventes.filter(ativo=True).order_by("nome"):
        minutos = carga.get(escrevente.id, 0)
        escreventes.append(
            {
                "nome": escrevente.nome,
                "minutos": minutos,
                "horas": minutos // 60,
                "minutos_resto": minutos % 60,
            }
        )
    escreventes.sort(key=lambda item: -item["minutos"])

    protocolos_recentes = Protocolo.objects.filter(cartorio=cartorio).select_related(
        "natureza", "escrevente_responsavel"
    )[:20]

    return render(
        request,
        "nucleo/dashboard.html",
        {"escreventes": escreventes, "protocolos_recentes": protocolos_recentes},
    )


@login_required
def lancar_protocolo(request):
    cartorio = _cartorio_do_usuario(request)

    if request.method == "POST":
        form = LancarProtocoloForm(request.POST, cartorio=cartorio)
        if form.is_valid():
            natureza = form.cleaned_data["natureza"]
            try:
                with transaction.atomic():
                    protocolo = Protocolo.objects.create(
                        cartorio=cartorio,
                        numero=form.cleaned_data["numero"],
                        natureza=natureza,
                        urgente=form.cleaned_data["urgente"],
                        tempo_estimado_minutos=natureza.tempo_estimado_minutos,
                    )
            except IntegrityError:
                form.add_error("numero", "Já existe um protocolo com esse número.")
                return render(request, "nucleo/lancar_protocolo.html", {"form": form})

            try:
                distribuicao.distribuir(protocolo)
            except distribuicao.SemEscreventeDisponivelError as erro:
                messages.error(request, str(erro))
            else:
                messages.success(
                    request,
                    f"Protocolo {protocolo.numero} foi distribuído para "
                    f"{protocolo.escrevente_responsavel.nome}.",
                )
            return redirect("dashboard")
    else:
        form = LancarProtocoloForm(cartorio=cartorio)

    return render(request, "nucleo/lancar_protocolo.html", {"form": form})
