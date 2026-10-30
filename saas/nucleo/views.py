"""
Views operacionais do dia a dia (nao sao telas de configuracao -- essas
ficam no Django Admin, ver admin.py).
"""

import json

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from . import distribuicao
from .models import Escrevente, Ferias, Grupo, Natureza, Protocolo, cartorio_do_usuario


class LancarProtocoloForm(forms.Form):
    numero = forms.CharField(label="Número do protocolo", max_length=50)
    natureza = forms.ModelChoiceField(
        label="Natureza formal do título",
        queryset=Natureza.objects.none(),
        widget=forms.Select(attrs={"id": "id_natureza"}),
    )
    inventario = forms.BooleanField(
        label="É inventário? (se sim, vira Complexo)",
        required=False,
        widget=forms.CheckboxInput(attrs={"id": "id_inventario"}),
    )
    matriculas = forms.IntegerField(label="Quantas matrículas?", min_value=1, initial=1)
    partes = forms.IntegerField(label="Quantas partes (outorgantes + outorgados)?", min_value=1, initial=1)
    urgente = forms.BooleanField(label="Urgente", required=False)

    def __init__(self, *args, cartorio=None, **kwargs):
        super().__init__(*args, **kwargs)

        queryset = (
            Natureza.objects.filter(cartorio=cartorio)
            .select_related("grupo", "grupo_se_inventario")
            .order_by("grupo__nome", "nome")
        )
        self.fields["natureza"].queryset = queryset
        # Agrupa as opcoes do <select> por Grupo (optgroup nativo), para
        # a pessoa ver as naturezas organizadas por simples/complexo/etc.
        # em vez de uma lista unica de ~90 itens.
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
    cartorio = cartorio_do_usuario(request.user)
    if not cartorio.configuracao_concluida:
        return redirect("configuracao_inicial")

    carga = distribuicao.carga_atual_dias(cartorio)
    contadores = distribuicao.contadores_protocolos(cartorio)
    hoje = timezone.localdate()

    escreventes = []
    for escrevente in cartorio.escreventes.filter(ativo=True).order_by("nome"):
        dias = carga.get(escrevente.id, 0)
        info_ferias = distribuicao.ferias_info(escrevente, hoje)
        contagem = contadores.get(escrevente.id, {"abertos": 0, "urgentes": 0})
        escreventes.append(
            {
                "nome": escrevente.nome,
                "dias": dias,
                "abertos": contagem["abertos"],
                "urgentes": contagem["urgentes"],
                "em_ferias": bool(info_ferias and info_ferias.em_ferias),
            }
        )
    escreventes.sort(key=lambda item: -item["dias"])

    maior_carga = max((e["dias"] for e in escreventes), default=0) or 1
    for escrevente in escreventes:
        fracao = escrevente["dias"] / maior_carga
        escrevente["percentual"] = round(min(100, fracao * 100))
        escrevente["cor"] = distribuicao.cor_carga(fracao)

    # Grupos sem nenhum escrevente ativo travam a distribuicao assim que
    # alguem tentar lancar um protocolo daquele tipo -- melhor avisar
    # aqui, antes disso acontecer, do que deixar a pessoa descobrir via
    # erro.
    grupos_vazios = cartorio.grupos.exclude(escreventes__ativo=True).order_by("nome")

    protocolos_recentes = Protocolo.objects.filter(cartorio=cartorio).select_related(
        "natureza", "escrevente_responsavel"
    ).order_by("-urgente", "-criado_em")[:20]

    # Confirmacao da ultima distribuicao, guardada na sessao por
    # lancar_protocolo() e consumida (pop) uma unica vez aqui -- da pra
    # mostrar um texto pronto pra copiar sem precisar de outra tabela.
    confirmacao = request.session.pop("confirmacao_distribuicao", None)

    return render(
        request,
        "nucleo/dashboard.html",
        {
            "escreventes": escreventes,
            "protocolos_recentes": protocolos_recentes,
            "grupos_vazios": grupos_vazios,
            "confirmacao": confirmacao,
        },
    )


def _dados_js_lancar_protocolo(cartorio):
    """JSON embutido na pagina para o calculo ao vivo do peso estimado,
    sem precisar de um round-trip ao servidor a cada tecla."""
    naturezas = Natureza.objects.filter(cartorio=cartorio).select_related("grupo", "grupo_se_inventario")
    dados_naturezas = {
        str(n.id): {
            "pesoBase": n.peso_base_dias,
            "grupoId": n.grupo_id,
            "grupoInventarioId": n.grupo_se_inventario_id,
        }
        for n in naturezas
    }
    dados_grupos = {
        str(g.id): {"extraMatricula": g.peso_extra_matricula_dias, "extraParte": g.peso_extra_parte_dias}
        for g in Grupo.objects.filter(cartorio=cartorio)
    }
    return json.dumps(dados_naturezas), json.dumps(dados_grupos)


@login_required
def lancar_protocolo(request):
    cartorio = cartorio_do_usuario(request.user)
    dados_naturezas_json, dados_grupos_json = _dados_js_lancar_protocolo(cartorio)
    contexto_extra = {"dados_naturezas_json": dados_naturezas_json, "dados_grupos_json": dados_grupos_json}

    if request.method == "POST":
        form = LancarProtocoloForm(request.POST, cartorio=cartorio)
        if form.is_valid():
            natureza = form.cleaned_data["natureza"]
            matriculas = form.cleaned_data["matriculas"]
            partes = form.cleaned_data["partes"]

            grupo_efetivo = natureza.grupo
            if form.cleaned_data["inventario"] and natureza.grupo_se_inventario_id:
                grupo_efetivo = natureza.grupo_se_inventario

            peso = distribuicao.peso_protocolo(natureza, matriculas, partes, grupo=grupo_efetivo)

            try:
                with transaction.atomic():
                    protocolo = Protocolo.objects.create(
                        cartorio=cartorio,
                        numero=form.cleaned_data["numero"],
                        natureza=natureza,
                        urgente=form.cleaned_data["urgente"],
                        matriculas=matriculas,
                        partes=partes,
                        peso_dias=peso,
                    )
            except IntegrityError:
                form.add_error("numero", "Já existe um protocolo com esse número.")
                return render(request, "nucleo/lancar_protocolo.html", {"form": form, **contexto_extra})

            try:
                distribuicao.distribuir(protocolo, grupo=grupo_efetivo)
            except distribuicao.SemEscreventeDisponivelError as erro:
                messages.error(request, str(erro))
            else:
                request.session["confirmacao_distribuicao"] = {
                    "numero": protocolo.numero,
                    "escrevente": protocolo.escrevente_responsavel.nome,
                    "data": timezone.localtime(protocolo.criado_em).strftime("%d/%m"),
                }
            return redirect("dashboard")
    else:
        form = LancarProtocoloForm(cartorio=cartorio)

    return render(request, "nucleo/lancar_protocolo.html", {"form": form, **contexto_extra})


@login_required
def historico(request):
    cartorio = cartorio_do_usuario(request.user)

    if request.method == "POST":
        protocolo = get_object_or_404(Protocolo, cartorio=cartorio, pk=request.POST.get("protocolo_id"))
        novo_status = request.POST.get("status")
        if novo_status in dict(Protocolo.STATUS_CHOICES):
            if novo_status != Protocolo.STATUS_ABERTO and protocolo.status == Protocolo.STATUS_ABERTO:
                protocolo.data_conclusao = timezone.localdate()
            elif novo_status == Protocolo.STATUS_ABERTO:
                protocolo.data_conclusao = None
            protocolo.status = novo_status
            protocolo.save(update_fields=["status", "data_conclusao"])
        return redirect("historico")

    protocolos = (
        Protocolo.objects.filter(cartorio=cartorio)
        .select_related("natureza", "escrevente_responsavel")
        .order_by("-criado_em")
    )
    return render(request, "nucleo/historico.html", {"protocolos": protocolos})


@login_required
def ferias(request):
    cartorio = cartorio_do_usuario(request.user)

    if request.method == "POST":
        if request.POST.get("remover"):
            Ferias.objects.filter(cartorio=cartorio, pk=request.POST["remover"]).delete()
        else:
            escrevente = get_object_or_404(Escrevente, cartorio=cartorio, pk=request.POST.get("escrevente"))
            inicio = request.POST.get("inicio")
            fim = request.POST.get("fim")
            if inicio and fim:
                Ferias.objects.create(cartorio=cartorio, escrevente=escrevente, inicio=inicio, fim=fim)
        return redirect("ferias")

    periodos = []
    for periodo in Ferias.objects.filter(cartorio=cartorio).select_related("escrevente").order_by("-inicio"):
        periodos.append(
            {
                "id": periodo.id,
                "escrevente_nome": periodo.escrevente.nome,
                "inicio": periodo.inicio,
                "fim": periodo.fim,
                "dias": (periodo.fim - periodo.inicio).days + 1,
            }
        )
    escreventes = Escrevente.objects.filter(cartorio=cartorio).order_by("nome")
    return render(request, "nucleo/ferias.html", {"periodos": periodos, "escreventes": escreventes})


class EscreventeInicialForm(forms.Form):
    nome = forms.CharField(label="Nome", max_length=200, required=False)
    grupos = forms.ModelMultipleChoiceField(
        label="Grupos", queryset=Grupo.objects.none(), required=False, widget=forms.CheckboxSelectMultiple
    )

    def __init__(self, *args, cartorio=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["grupos"].queryset = Grupo.objects.filter(cartorio=cartorio).order_by("nome")


EscreventeFormSet = forms.formset_factory(EscreventeInicialForm, extra=3)


@login_required
def configuracao_inicial(request):
    """Primeira tela que um cartorio novo ve, em vez do Painel vazio --
    cadastra a equipe e ja distribui cada pessoa nos grupos certos, num
    unico formulario. So aparece ate cartorio.configuracao_concluida
    virar True (ver dashboard); depois disso, adicionar gente e so pelo
    Admin mesmo (Escreventes + Grupos), como ja funcionava antes."""
    cartorio = cartorio_do_usuario(request.user)

    if request.method == "POST":
        if request.POST.get("pular"):
            cartorio.configuracao_concluida = True
            cartorio.save(update_fields=["configuracao_concluida"])
            return redirect("dashboard")

        formset = EscreventeFormSet(request.POST, form_kwargs={"cartorio": cartorio})
        if formset.is_valid():
            criados = 0
            for linha in formset.cleaned_data:
                nome = (linha.get("nome") or "").strip()
                if not nome:
                    continue
                escrevente = Escrevente.objects.create(cartorio=cartorio, nome=nome)
                escrevente.grupos.set(linha.get("grupos") or [])
                criados += 1

            cartorio.configuracao_concluida = True
            cartorio.save(update_fields=["configuracao_concluida"])
            if criados:
                plural = "" if criados == 1 else "s"
                messages.success(request, f"{criados} pessoa{plural} cadastrada{plural} na equipe.")
            return redirect("dashboard")
    else:
        formset = EscreventeFormSet(form_kwargs={"cartorio": cartorio})

    return render(request, "nucleo/configuracao_inicial.html", {"formset": formset})


@login_required
def sincronizar(request):
    return render(request, "nucleo/sincronizar.html", {})
