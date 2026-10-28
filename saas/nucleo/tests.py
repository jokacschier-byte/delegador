from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .dados_padrao import GRUPOS_PADRAO, NATUREZAS_PADRAO, carregar_catalogo_padrao
from .distribuicao import SemEscreventeDisponivelError, escolher_escrevente
from .management.commands.criar_cartorio import _garantir_grupo_admin_cartorio
from .models import Cartorio, Escrevente, Grupo, Natureza, Perfil, Protocolo


def _criar_tenant(nome, usuario):
    cartorio = Cartorio.objects.create(nome=nome)
    user = User.objects.create_user(username=usuario, password="SenhaForte123", is_staff=True)
    Perfil.objects.create(user=user, cartorio=cartorio)
    user.groups.add(_garantir_grupo_admin_cartorio())
    return cartorio, user


class DistribuicaoTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Teste", "admin_teste")

        self.ana = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana")
        self.bruno = Escrevente.objects.create(cartorio=self.cartorio, nome="Bruno")

        self.grupo_simples = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        self.grupo_simples.escreventes.set([self.ana, self.bruno])

        self.natureza = Natureza.objects.create(
            cartorio=self.cartorio,
            nome="Abertura de Matrícula",
            grupo=self.grupo_simples,
            tempo_estimado_minutos=40,
        )

    def _lancar(self, numero):
        return Protocolo.objects.create(
            cartorio=self.cartorio,
            numero=numero,
            natureza=self.natureza,
            tempo_estimado_minutos=self.natureza.tempo_estimado_minutos,
        )

    def test_escolhe_sempre_quem_tem_menos_carga(self):
        p1 = self._lancar("1")
        escolhido1 = escolher_escrevente(p1)
        p1.escrevente_responsavel = escolhido1
        p1.save()

        p2 = self._lancar("2")
        escolhido2 = escolher_escrevente(p2)

        # como so tem Ana e Bruno com carga 0 no inicio, o primeiro
        # protocolo vai para o primeiro da lista (Ana); o segundo deve
        # ir para quem ainda esta com carga zero (Bruno).
        self.assertEqual(escolhido1, self.ana)
        self.assertEqual(escolhido2, self.bruno)

    def test_grupo_sem_escrevente_ativo_levanta_erro(self):
        grupo_vazio = Grupo.objects.create(cartorio=self.cartorio, nome="Vazio")
        natureza_sem_equipe = Natureza.objects.create(
            cartorio=self.cartorio, nome="Caso Raro", grupo=grupo_vazio, tempo_estimado_minutos=30
        )
        protocolo = Protocolo.objects.create(
            cartorio=self.cartorio,
            numero="99",
            natureza=natureza_sem_equipe,
            tempo_estimado_minutos=30,
        )
        with self.assertRaises(SemEscreventeDisponivelError):
            escolher_escrevente(protocolo)


class IsolamentoEntreCartoriosTests(TestCase):
    """Garante que um cartorio nunca ve dados de outro -- isso e o
    requisito de seguranca mais importante de um SaaS multi-tenant."""

    def setUp(self):
        self.cartorio_a, self.user_a = _criar_tenant("Cartorio A", "admin_a_teste")
        self.cartorio_b, self.user_b = _criar_tenant("Cartorio B", "admin_b_teste")

        self.escrevente_a = Escrevente.objects.create(cartorio=self.cartorio_a, nome="Escrevente A")
        self.escrevente_b = Escrevente.objects.create(cartorio=self.cartorio_b, nome="Escrevente B")

        grupo_a = Grupo.objects.create(cartorio=self.cartorio_a, nome="Simples")
        grupo_a.escreventes.add(self.escrevente_a)
        grupo_b = Grupo.objects.create(cartorio=self.cartorio_b, nome="Simples")
        grupo_b.escreventes.add(self.escrevente_b)

        self.natureza_a = Natureza.objects.create(
            cartorio=self.cartorio_a, nome="Natureza A", grupo=grupo_a, tempo_estimado_minutos=40
        )
        Natureza.objects.create(
            cartorio=self.cartorio_b, nome="Natureza B", grupo=grupo_b, tempo_estimado_minutos=40
        )

        Protocolo.objects.create(
            cartorio=self.cartorio_a,
            numero="A-1",
            natureza=self.natureza_a,
            tempo_estimado_minutos=40,
            escrevente_responsavel=self.escrevente_a,
        )

    def test_admin_de_um_cartorio_nao_ve_escreventes_do_outro(self):
        client = Client()
        client.login(username="admin_a_teste", password="SenhaForte123")

        resposta = client.get(reverse("admin:nucleo_escrevente_changelist"))

        self.assertContains(resposta, "Escrevente A")
        self.assertNotContains(resposta, "Escrevente B")

    def test_dashboard_so_mostra_protocolos_do_proprio_cartorio(self):
        client = Client()
        client.login(username="admin_b_teste", password="SenhaForte123")

        resposta = client.get(reverse("dashboard"))

        self.assertNotContains(resposta, "A-1")

    def test_lancar_protocolo_so_oferece_naturezas_do_proprio_cartorio(self):
        client = Client()
        client.login(username="admin_b_teste", password="SenhaForte123")

        resposta = client.get(reverse("lancar_protocolo"))

        self.assertNotContains(resposta, "Natureza A")

    def test_admin_nao_pode_editar_cartorio_ou_perfil(self):
        client = Client()
        client.login(username="admin_a_teste", password="SenhaForte123")

        resposta = client.get(reverse("admin:index"))

        self.assertNotContains(resposta, "Cartorios")
        self.assertNotContains(resposta, "Perfis")


class CatalogoPadraoTests(TestCase):
    def test_carregar_catalogo_e_idempotente_e_sem_escreventes(self):
        cartorio = Cartorio.objects.create(nome="Cartorio Catalogo")

        grupos_criados, naturezas_criadas = carregar_catalogo_padrao(cartorio)
        self.assertEqual(grupos_criados, len(GRUPOS_PADRAO))
        self.assertEqual(naturezas_criadas, len(NATUREZAS_PADRAO))

        # chamar de novo nao deve duplicar nada
        grupos_de_novo, naturezas_de_novo = carregar_catalogo_padrao(cartorio)
        self.assertEqual((grupos_de_novo, naturezas_de_novo), (0, 0))

        self.assertEqual(Grupo.objects.filter(cartorio=cartorio).count(), len(GRUPOS_PADRAO))
        self.assertEqual(Natureza.objects.filter(cartorio=cartorio).count(), len(NATUREZAS_PADRAO))
        self.assertEqual(Escrevente.objects.filter(cartorio=cartorio).count(), 0)

    def test_unificacao_e_sempre_simples_no_catalogo(self):
        cartorio = Cartorio.objects.create(nome="Cartorio Unificacao")
        carregar_catalogo_padrao(cartorio)

        unificacao = Natureza.objects.get(cartorio=cartorio, nome="Unificação")
        self.assertEqual(unificacao.grupo.nome, "Simples")

    def test_criar_cartorio_carrega_catalogo_por_padrao(self):
        call_command("criar_cartorio", nome="Cartorio CLI", usuario="cli_teste", senha="SenhaForte123")

        cartorio = Perfil.objects.get(user__username="cli_teste").cartorio
        self.assertEqual(Natureza.objects.filter(cartorio=cartorio).count(), len(NATUREZAS_PADRAO))
        self.assertEqual(Escrevente.objects.filter(cartorio=cartorio).count(), 0)

    def test_criar_cartorio_sem_catalogo_padrao(self):
        call_command(
            "criar_cartorio",
            nome="Cartorio Vazio",
            usuario="cli_vazio_teste",
            senha="SenhaForte123",
            sem_catalogo_padrao=True,
        )

        cartorio = Perfil.objects.get(user__username="cli_vazio_teste").cartorio
        self.assertEqual(Natureza.objects.filter(cartorio=cartorio).count(), 0)

    def test_comando_carregar_catalogo_padrao_para_cartorio_existente(self):
        call_command(
            "criar_cartorio",
            nome="Cartorio Retrofit",
            usuario="retrofit_teste",
            senha="SenhaForte123",
            sem_catalogo_padrao=True,
        )
        call_command("carregar_catalogo_padrao", usuario="retrofit_teste")

        cartorio = Perfil.objects.get(user__username="retrofit_teste").cartorio
        self.assertEqual(Natureza.objects.filter(cartorio=cartorio).count(), len(NATUREZAS_PADRAO))


class LancarProtocoloViewTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio View", "admin_view_teste")
        self.escrevente = Escrevente.objects.create(cartorio=self.cartorio, nome="Única")
        grupo = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        grupo.escreventes.add(self.escrevente)
        self.natureza = Natureza.objects.create(
            cartorio=self.cartorio, nome="Doação", grupo=grupo, tempo_estimado_minutos=40
        )
        self.client = Client()
        self.client.login(username="admin_view_teste", password="SenhaForte123")

    def test_lancar_protocolo_distribui_e_redireciona(self):
        resposta = self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": self.natureza.pk, "urgente": ""},
        )
        self.assertRedirects(resposta, reverse("dashboard"))

        protocolo = Protocolo.objects.get(cartorio=self.cartorio, numero="123")
        self.assertEqual(protocolo.escrevente_responsavel, self.escrevente)

    def test_dashboard_mostra_chip_de_copiar_apos_distribuir(self):
        self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": self.natureza.pk, "urgente": ""},
        )

        resposta = self.client.get(reverse("dashboard"))
        hoje = timezone.localtime(timezone.now()).strftime("%d/%m")

        self.assertContains(resposta, f"cadastrado em {hoje} - mesa de Única")
        self.assertContains(resposta, "data-copiar=")

    def test_chip_de_copiar_some_depois_de_uma_visita(self):
        self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": self.natureza.pk, "urgente": ""},
        )
        self.client.get(reverse("dashboard"))

        resposta = self.client.get(reverse("dashboard"))

        self.assertNotContains(resposta, "data-copiar=")

    def test_numero_duplicado_mostra_erro_sem_quebrar(self):
        self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": self.natureza.pk, "urgente": ""},
        )
        resposta = self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": self.natureza.pk, "urgente": ""},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Já existe um protocolo com esse número.")

    def test_natureza_invalida_mostra_erro_sem_quebrar(self):
        resposta = self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": "99999", "urgente": ""},
        )
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "escolha válida")
        self.assertFalse(Protocolo.objects.filter(cartorio=self.cartorio, numero="123").exists())

    def test_natureza_de_outro_cartorio_e_rejeitada(self):
        outro_cartorio, _ = _criar_tenant("Cartorio Outro", "admin_outro_teste")
        outro_grupo = Grupo.objects.create(cartorio=outro_cartorio, nome="Simples")
        natureza_de_outro = Natureza.objects.create(
            cartorio=outro_cartorio, nome="Natureza de outro cartorio", grupo=outro_grupo, tempo_estimado_minutos=40
        )

        resposta = self.client.post(
            reverse("lancar_protocolo"),
            {"numero": "123", "natureza": natureza_de_outro.pk, "urgente": ""},
        )

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "escolha válida")
        self.assertFalse(Protocolo.objects.filter(cartorio=self.cartorio, numero="123").exists())

    def test_select_de_natureza_agrupado_por_grupo(self):
        Natureza.objects.create(
            cartorio=self.cartorio,
            nome="Formal de Partilha - Inventário",
            grupo=Grupo.objects.create(cartorio=self.cartorio, nome="Complexo"),
            tempo_estimado_minutos=120,
        )

        resposta = self.client.get(reverse("lancar_protocolo"))

        self.assertContains(resposta, '<optgroup label="Simples">')
        self.assertContains(resposta, '<optgroup label="Complexo">')


class DashboardAvisosTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Avisos", "admin_avisos_teste")
        self.client = Client()
        self.client.login(username="admin_avisos_teste", password="SenhaForte123")

    def test_avisa_quando_grupo_nao_tem_escrevente_ativo(self):
        Grupo.objects.create(cartorio=self.cartorio, nome="Complexo")

        resposta = self.client.get(reverse("dashboard"))

        self.assertContains(resposta, "sem escrevente ativo")
        self.assertContains(resposta, "Complexo")

    def test_nao_avisa_quando_todos_os_grupos_tem_escrevente_ativo(self):
        escrevente = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana", ativo=True)
        grupo = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        grupo.escreventes.add(escrevente)

        resposta = self.client.get(reverse("dashboard"))

        self.assertNotContains(resposta, "sem escrevente ativo")

    def test_grupo_so_com_escrevente_inativo_ainda_conta_como_vazio(self):
        escrevente = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana", ativo=False)
        grupo = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        grupo.escreventes.add(escrevente)

        resposta = self.client.get(reverse("dashboard"))

        self.assertContains(resposta, "sem escrevente ativo")


class OrdenacaoUrgenteTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Urgente", "admin_urgente_teste")
        escrevente = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana")
        grupo = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        grupo.escreventes.add(escrevente)
        natureza = Natureza.objects.create(
            cartorio=self.cartorio, nome="Doação", grupo=grupo, tempo_estimado_minutos=40
        )
        Protocolo.objects.create(
            cartorio=self.cartorio, numero="1", natureza=natureza, tempo_estimado_minutos=40
        )
        Protocolo.objects.create(
            cartorio=self.cartorio, numero="2", natureza=natureza, tempo_estimado_minutos=40, urgente=True
        )

    def test_protocolo_urgente_aparece_antes_na_lista_mesmo_sendo_mais_antigo(self):
        client = Client()
        client.login(username="admin_urgente_teste", password="SenhaForte123")

        resposta = client.get(reverse("dashboard"))

        posicao_urgente = resposta.content.decode().find(">2 <span")
        posicao_normal = resposta.content.decode().find(">1</td>")
        self.assertNotEqual(posicao_urgente, -1)
        self.assertNotEqual(posicao_normal, -1)
        self.assertLess(posicao_urgente, posicao_normal)
