"""
Modelos do SaaS de distribuicao inteligente de protocolos.

Cada "Cartorio" e um tenant: tudo que pertence a um cartorio (usuarios,
escreventes, grupos, naturezas, protocolos) e isolado dos outros. Nunca
faca uma consulta aqui sem filtrar por cartorio -- as views e o admin
(ver admin.py) sao responsaveis por garantir esse filtro.

Unidade de carga: dias (nao minutos). Um protocolo tem um "peso" em
dias = peso_base_dias da Natureza + ajustes por matricula/parte extra
(definidos por Grupo). Essa e a mesma logica validada na ferramenta
local que o cartorio ja usava no dia a dia.
"""

from django.contrib.auth.models import User
from django.db import models


class Cartorio(models.Model):
    nome = models.CharField(max_length=200)
    criado_em = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return self.nome


class Perfil(models.Model):
    """Liga um usuario do Django a um cartorio (tenant)."""

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="perfis")

    def __str__(self) -> str:
        return f"{self.user.username} ({self.cartorio.nome})"


def cartorio_do_usuario(usuario) -> Cartorio | None:
    """Cartorio ligado ao Perfil desse usuario, ou None se ele nao tiver
    um (ex.: superuser sem Perfil associado)."""
    perfil = getattr(usuario, "perfil", None)
    return perfil.cartorio if perfil else None


class Escrevente(models.Model):
    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="escreventes")
    nome = models.CharField(max_length=200)
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ("cartorio", "nome")
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Grupo(models.Model):
    """Um grupo de competencia (ex.: "Simples", "Complexo").

    Definido pelo proprio cartorio-cliente -- nao e mais fixo no codigo.
    Os pesos extras (por matricula/parte alem da primeira) tambem sao
    por grupo, porque um grupo mais complexo tende a ganhar mais tempo
    por item extra do que um grupo simples.
    """

    MODO_CARGA = "CARGA"
    MODO_PROPORCAO = "PROPORCAO"
    MODO_CHOICES = [
        (MODO_CARGA, "Por carga (padrão)"),
        (MODO_PROPORCAO, "Por proporção manual"),
    ]

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="grupos")
    nome = models.CharField(max_length=100)
    escreventes = models.ManyToManyField(Escrevente, related_name="grupos", blank=True)
    peso_extra_matricula_dias = models.FloatField(
        default=0, help_text="Dias somados ao peso do protocolo por matricula alem da primeira."
    )
    peso_extra_parte_dias = models.FloatField(
        default=0, help_text="Dias somados ao peso do protocolo por parte (outorgante/outorgado) alem da primeira."
    )
    # Por padrao a distribuicao escolhe quem tem menor carga atual. Em
    # MODO_PROPORCAO, troca esse criterio final por uma proporcao fixa
    # configurada em CotaDistribuicao (ex.: 2 para uma pessoa, 3 para
    # outra), para quando a carga/peso nao reflete bem a capacidade real
    # (alguem que faz outras tarefas alem de analisar protocolos).
    modo_distribuicao = models.CharField(
        max_length=20, choices=MODO_CHOICES, default=MODO_CARGA, verbose_name="modo de distribuição"
    )

    class Meta:
        unique_together = ("cartorio", "nome")
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class CotaDistribuicao(models.Model):
    """Peso relativo de um escrevente na distribuicao por proporcao
    manual (Grupo.modo_distribuicao == MODO_PROPORCAO).

    Quem nao tem uma linha aqui usa cota 1 por padrao (round-robin
    simples) -- ver nucleo.distribuicao._escolher_por_proporcao.
    """

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="cotas_distribuicao")
    grupo = models.ForeignKey(Grupo, on_delete=models.CASCADE, related_name="cotas")
    escrevente = models.ForeignKey(Escrevente, on_delete=models.CASCADE, related_name="cotas")
    cota = models.PositiveIntegerField(
        default=1,
        help_text="Peso relativo na distribuição por proporção (ex.: 2 e 3 = a cada 5 protocolos, 2 vão para um e 3 para o outro).",
    )

    class Meta:
        unique_together = ("grupo", "escrevente")
        verbose_name = "Cota de distribuição"
        verbose_name_plural = "Cotas de distribuição"

    def __str__(self) -> str:
        return f"{self.escrevente.nome} ({self.cota}) em {self.grupo.nome}"


class Natureza(models.Model):
    """Um tipo de protocolo (ex.: "Averbação de Divórcio"), mapeado para
    o grupo que deve analisa-lo e com um peso base (em dias)."""

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="naturezas")
    nome = models.CharField(max_length=200)
    grupo = models.ForeignKey(Grupo, on_delete=models.PROTECT, related_name="naturezas")
    peso_base_dias = models.FloatField(default=3)
    # Quando preenchido, o formulario "Lancar protocolo" mostra "E
    # inventario?" para esta natureza; se marcado, usa este grupo em vez
    # do grupo padrao (ex.: Carta de Adjudicacao normalmente e Simples,
    # mas vira Complexo quando ligada a um inventario).
    grupo_se_inventario = models.ForeignKey(
        Grupo, on_delete=models.PROTECT, null=True, blank=True, related_name="naturezas_alternativas"
    )
    # Quantos protocolos concluidos ja entraram na media de peso_base_dias.
    # Ainda nao e preenchido por nenhum codigo -- preparado para a futura
    # sincronizacao com o SRI (ver README: "O que falta para producao"),
    # que recalibrara peso_base_dias com dados reais de conclusao. Ate la,
    # 0 significa que o valor e so um palpite inicial.
    amostras = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("cartorio", "nome")
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Protocolo(models.Model):
    STATUS_ABERTO = "ABERTO"
    STATUS_CONCLUIDO = "CONCLUIDO"
    STATUS_DILIGENCIA = "DILIGENCIA"
    STATUS_CHOICES = [
        (STATUS_ABERTO, "Em aberto"),
        (STATUS_CONCLUIDO, "Concluído"),
        (STATUS_DILIGENCIA, "Diligência"),
    ]

    TIPO_NOVO = "NOVO"
    TIPO_REINGRESSO = "REINGRESSO"
    TIPO_CHOICES = [
        (TIPO_NOVO, "Novo"),
        (TIPO_REINGRESSO, "Reingresso"),
    ]

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="protocolos")
    numero = models.CharField(max_length=50)
    natureza = models.ForeignKey(Natureza, on_delete=models.PROTECT, related_name="protocolos")
    urgente = models.BooleanField(default=False)
    escrevente_responsavel = models.ForeignKey(
        Escrevente, on_delete=models.SET_NULL, null=True, blank=True, related_name="protocolos"
    )
    matriculas = models.PositiveIntegerField(default=1)
    partes = models.PositiveIntegerField(default=1)
    # Copiado/calculado no momento do lancamento (base da natureza + ajuste
    # por matricula/parte extra), para que uma mudanca futura nos pesos
    # padrao nao reescreva o historico.
    peso_dias = models.FloatField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ABERTO)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default=TIPO_NOVO)
    data_conclusao = models.DateField(null=True, blank=True)
    observacao = models.CharField(max_length=300, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cartorio", "numero")
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"{self.numero} ({self.natureza})"


class Ferias(models.Model):
    """Um periodo de ferias de um escrevente.

    Usado para suspender temporariamente as sugestoes automaticas de
    distribuicao para essa pessoa -- ver nucleo.distribuicao.ferias_info.
    """

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="ferias")
    escrevente = models.ForeignKey(Escrevente, on_delete=models.CASCADE, related_name="ferias")
    inicio = models.DateField()
    fim = models.DateField()

    class Meta:
        ordering = ["-inicio"]
        verbose_name = "Período de férias"
        verbose_name_plural = "Períodos de férias"

    def __str__(self) -> str:
        return f"{self.escrevente.nome}: {self.inicio} a {self.fim}"
