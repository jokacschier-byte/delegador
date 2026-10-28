"""
Carrega (ou recarrega) o catalogo padrao de grupos/naturezas num
cartorio que ja existe -- util para um cartorio criado antes dessa
funcionalidade, ou com --sem-catalogo-padrao na criacao.

Uso:
    python manage.py carregar_catalogo_padrao --usuario Cadastro
"""

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError

from nucleo.dados_padrao import carregar_catalogo_padrao


class Command(BaseCommand):
    help = "Carrega o catalogo padrao de grupos/naturezas no cartorio de um usuario."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", required=True, help="Login do administrador do cartório.")

    def handle(self, *args, **options):
        try:
            user = User.objects.select_related("perfil__cartorio").get(username=options["usuario"])
        except User.DoesNotExist:
            raise CommandError(f"Usuário '{options['usuario']}' não existe.")

        perfil = getattr(user, "perfil", None)
        if perfil is None:
            raise CommandError(f"Usuário '{options['usuario']}' não está ligado a nenhum cartório.")

        grupos_criados, naturezas_criadas = carregar_catalogo_padrao(perfil.cartorio)
        self.stdout.write(
            self.style.SUCCESS(
                f"Cartório '{perfil.cartorio.nome}': {grupos_criados} grupo(s) novo(s) e "
                f"{naturezas_criadas} natureza(s) nova(s) carregada(s)."
            )
        )
