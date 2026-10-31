from django.db import migrations


def marcar_cartorios_existentes_como_configurados(apps, schema_editor):
    # O campo configuracao_concluida (migracao anterior) nasceu com
    # default=False pra TODO mundo, inclusive cartorios que ja estavam
    # ativos em producao -- isso jogava quem ja usava o sistema de volta
    # pra tela de "monte sua equipe". Cartorios que ja existem na hora
    # dessa migracao rodar sao, por definicao, anteriores a essa
    # funcionalidade: marca todos como ja configurados. So cartorios
    # criados depois disso (via criar_cartorio) continuam nascendo com
    # False, do jeito que a tela foi pensada.
    Cartorio = apps.get_model("nucleo", "Cartorio")
    Cartorio.objects.update(configuracao_concluida=True)


class Migration(migrations.Migration):

    dependencies = [
        ("nucleo", "0004_cartorio_configuracao_concluida"),
    ]

    operations = [
        migrations.RunPython(marcar_cartorios_existentes_como_configurados, migrations.RunPython.noop),
    ]
