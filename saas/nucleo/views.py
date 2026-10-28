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
    natureza = forms.ModelChoiceField(
        label="Natureza",
        queryset=Natureza.objects.none(),
        widget=forms.Select(attrs={"id": "id_natureza"}),
    )
    urgente = forms.BooleanField(label="Urgente", required=False)

    def __init__(self, *args, cartorio=None, **kwargs):
        super().__init__(*args, **kwargs)

        queryset = (
            Natureza.objects.filter(cartorio=cartorio)
            .select_related("grupo")
            .order_by("grupo__nome", "nome")
        )
        self.fields["natureza"].queryset = queryset
        # Agrupa as opcoes do <select> por Grupo (optgroup nativo), para
        # o escrevente ver as naturezas organizadas por simples/complexo/
        # etc. em vez de uma lista unica de ~70 itens.
        self.fields["natureza"].widget.choices = self._agrupar_por_grupo(queryset)

    @staticmethod
    def _agrupar_por_grupo(queryset):
        grupos: dict[str, list[tuple[int, str]]] = {}
        ordem_grupos: list[str] = []

        for natureza in queryset:
            nome_grupo = natureza.grupo.nome
            if nome_grupo not in grupos:
                grupos[nome_grupo] = []
                ordem_grupos.append(nome_grupo)
            grupos[nome_grupo].append((natureza.pk, natureza.nome))

        choices = [("", "Selecione a natureza…")]
        choices.extend((nome_grupo, grupos[nome_grupo]) for nome_grupo in ordem_grupos)
        return choices


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

    maior_carga = max((e["minutos"] for e in escreventes), default=0) or 1
    for escrevente in escreventes:
        escrevente["percentual"] = round(escrevente["minutos"] / maior_carga * 100)

    # Grupos sem nenhum escrevente ativo travam a distribuicao assim que
    # alguem tentar lancar um protocolo daquele tipo -- melhor avisar
    # aqui, antes disso acontecer, do que deixar a pessoa descobrir via
    # erro.
    grupos_vazios = cartorio.grupos.exclude(escreventes__ativo=True).order_by("nome")

    protocolos_recentes = Protocolo.objects.filter(cartorio=cartorio).select_related(
        "natureza", "escrevente_responsavel"
    ).order_by("-urgente", "-criado_em")[:20]

    return render(
        request,
        "nucleo/dashboard.html",
        {
            "escreventes": escreventes,
            "protocolos_recentes": protocolos_recentes,
            "grupos_vazios": grupos_vazios,
        },
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
