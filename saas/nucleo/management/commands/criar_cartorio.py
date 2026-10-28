"""
Onboarding de um novo cartorio-cliente: cria o Cartorio, o usuario
administrador desse cartorio e garante que ele so tenha permissao sobre
os modelos do proprio tenant (nunca sobre Cartorio/Perfil de outros
clientes).

Uso:
    python manage.py criar_cartorio --nome "Cartorio Exemplo" --usuario admin_exemplo --senha "trocar123"
"""

from django.contrib.auth.models import Group, Permission, User
from django.contrib.contenttypes.models import ContentType
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from nucleo.models import Cartorio, Escrevente, Grupo, Natureza, Perfil, Protocolo

NOME_GRUPO_ADMIN_CARTORIO = "Administradores de Cartorio"
MODELOS_PERMITIDOS = [Escrevente, Grupo, Natureza, Protocolo]


def _garantir_grupo_admin_cartorio() -> Group:
    grupo, _ = Group.objects.get_or_create(name=NOME_GRUPO_ADMIN_CARTORIO)

    permissoes = Permission.objects.filter(
        content_type__in=[ContentType.objects.get_for_model(modelo) for modelo in MODELOS_PERMITIDOS]
    )
    grupo.permissions.set(permissoes)
    return grupo


class Command(BaseCommand):
    help = "Cria um novo cartorio-cliente e o usuario administrador dele."

    def add_arguments(self, parser):
        parser.add_argument("--nome", required=True, help="Nome do cartorio (tenant).")
        parser.add_argument("--usuario", required=True, help="Nome de login do administrador do cartorio.")
        parser.add_argument("--senha", required=True, help="Senha inicial do administrador.")
        parser.add_argument("--email", default="", help="E-mail do administrador (opcional).")

    @transaction.atomic
    def handle(self, *args, **options):
        nome = options["nome"]
        usuario = options["usuario"]

        if User.objects.filter(username=usuario).exists():
            raise CommandError(f"Já existe um usuário com o login '{usuario}'.")

        cartorio = Cartorio.objects.create(nome=nome)

        user = User.objects.create_user(
            username=usuario,
            password=options["senha"],
            email=options["email"],
            is_staff=True,
        )
        Perfil.objects.create(user=user, cartorio=cartorio)

        grupo = _garantir_grupo_admin_cartorio()
        user.groups.add(grupo)

        self.stdout.write(
            self.style.SUCCESS(
                f"Cartorio '{nome}' criado (id={cartorio.id}). "
                f"Usuário '{usuario}' pode logar em /admin/ e em /, "
                "e só vê os dados desse cartório."
            )
        )
