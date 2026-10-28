"""
Modelos do SaaS de distribuicao inteligente de protocolos.

Cada "Cartorio" e um tenant: tudo que pertence a um cartorio (usuarios,
escreventes, grupos, naturezas, protocolos) e isolado dos outros. Nunca
faca uma consulta aqui sem filtrar por cartorio -- as views e o admin
(ver admin.py) sao responsaveis por garantir esse filtro.
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
    """Um grupo de competencia (ex.: "Simples", "Complexo", "Urgencias").

    Definido pelo proprio cartorio-cliente -- nao e mais fixo no codigo.
    """

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="grupos")
    nome = models.CharField(max_length=100)
    escreventes = models.ManyToManyField(Escrevente, related_name="grupos", blank=True)

    class Meta:
        unique_together = ("cartorio", "nome")
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Natureza(models.Model):
    """Um tipo de protocolo (ex.: "Averbação de Divórcio"), mapeado para
    o grupo que deve analisa-lo e com um tempo estimado padrao."""

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="naturezas")
    nome = models.CharField(max_length=200)
    grupo = models.ForeignKey(Grupo, on_delete=models.PROTECT, related_name="naturezas")
    tempo_estimado_minutos = models.PositiveIntegerField(default=60)

    class Meta:
        unique_together = ("cartorio", "nome")
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Protocolo(models.Model):
    STATUS_PENDENTE = "PENDENTE"
    STATUS_CONCLUIDO = "CONCLUIDO"
    STATUS_CHOICES = [
        (STATUS_PENDENTE, "Pendente"),
        (STATUS_CONCLUIDO, "Concluído"),
    ]

    cartorio = models.ForeignKey(Cartorio, on_delete=models.CASCADE, related_name="protocolos")
    numero = models.CharField(max_length=50)
    natureza = models.ForeignKey(Natureza, on_delete=models.PROTECT, related_name="protocolos")
    urgente = models.BooleanField(default=False)
    escrevente_responsavel = models.ForeignKey(
        Escrevente, on_delete=models.SET_NULL, null=True, blank=True, related_name="protocolos"
    )
    # Copiado da Natureza no momento do lancamento, para que uma mudanca
    # futura na estimativa padrao nao reescreva o historico.
    tempo_estimado_minutos = models.PositiveIntegerField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDENTE)
    observacao = models.CharField(max_length=300, blank=True, default="")
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("cartorio", "numero")
        ordering = ["-criado_em"]

    def __str__(self) -> str:
        return f"{self.numero} ({self.natureza})"
