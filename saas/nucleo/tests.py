from datetime import date, timedelta
from unittest.mock import patch

from django.contrib.auth.models import Group, Permission, User
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from . import distribuicao
from .dados_padrao import GRUPOS_PADRAO, NATUREZAS_PADRAO, carregar_catalogo_padrao
from .distribuicao import SemEscreventeDisponivelError, escolher_escrevente, peso_protocolo
from .management.commands.criar_cartorio import _garantir_grupo_admin_cartorio
from .models import Cartorio, CotaDistribuicao, Escrevente, Ferias, Grupo, Natureza, Perfil, Protocolo


def _criar_tenant(nome, usuario):
    cartorio = Cartorio.objects.create(nome=nome)
    user = User.objects.create_user(username=usuario, password="SenhaForte123", is_staff=True)
    Perfil.objects.create(user=user, cartorio=cartorio)
    user.groups.add(_garantir_grupo_admin_cartorio())
    return cartorio, user


class PesoProtocoloTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Peso", "admin_peso_teste")
        self.grupo = Grupo.objects.create(
            cartorio=self.cartorio, nome="Simples", peso_extra_matricula_dias=0.5, peso_extra_parte_dias=0.2
        )
        self.natureza = Natureza.objects.create(
            cartorio=self.cartorio, nome="Requerimento", grupo=self.grupo, peso_base_dias=3
        )

    def test_peso_base_sem_extras(self):
        self.assertEqual(peso_protocolo(self.natureza, matriculas=1, partes=1), 3.0)

    def test_peso_com_matriculas_e_partes_extras(self):
        # 3 + 0.5*(3-1) + 0.2*(2-1) = 3 + 1.0 + 0.2 = 4.2
        self.assertEqual(peso_protocolo(self.natureza, matriculas=3, partes=2), 4.2)

    def test_grupo_explicito_sobrepoe_o_da_natureza(self):
        grupo_complexo = Grupo.objects.create(
            cartorio=self.cartorio, nome="Complexo", peso_extra_matricula_dias=1.0, peso_extra_parte_dias=0.4
        )
        # mesma natureza, mas usando os pesos do grupo Complexo (caso "e inventario?")
        self.assertEqual(peso_protocolo(self.natureza, matriculas=2, partes=1, grupo=grupo_complexo), 4.0)


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
            peso_base_dias=3,
        )

    def _lancar(self, numero, status=Protocolo.STATUS_ABERTO, escrevente=None):
        return Protocolo.objects.create(
            cartorio=self.cartorio,
            numero=numero,
            natureza=self.natureza,
            peso_dias=peso_protocolo(self.natureza, 1, 1),
            status=status,
            escrevente_responsavel=escrevente,
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

    def test_protocolo_concluido_nao_conta_mais_na_carga(self):
        p1 = self._lancar("1", escrevente=self.ana)
        self.assertEqual(distribuicao.carga_atual_dias(self.cartorio).get(self.ana.id), 3.0)

        p1.status = Protocolo.STATUS_CONCLUIDO
        p1.save(update_fields=["status"])

        self.assertEqual(distribuicao.carga_atual_dias(self.cartorio).get(self.ana.id, 0), 0)

    def test_grupo_sem_escrevente_ativo_levanta_erro(self):
        grupo_vazio = Grupo.objects.create(cartorio=self.cartorio, nome="Vazio")
        natureza_sem_equipe = Natureza.objects.create(
            cartorio=self.cartorio, nome="Caso Raro", grupo=grupo_vazio, peso_base_dias=3
        )
        protocolo = Protocolo.objects.create(
            cartorio=self.cartorio,
            numero="99",
            natureza=natureza_sem_equipe,
            peso_dias=3,
        )
        with self.assertRaises(SemEscreventeDisponivelError):
            escolher_escrevente(protocolo)


class FeriasTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Ferias", "admin_ferias_teste")
        self.ana = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana")
        self.bruno = Escrevente.objects.create(cartorio=self.cartorio, nome="Bruno")
        self.grupo = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        self.grupo.escreventes.set([self.ana, self.bruno])
        self.natureza = Natureza.objects.create(
            cartorio=self.cartorio, nome="Requerimento", grupo=self.grupo, peso_base_dias=3
        )

    def _protocolo(self, numero, urgente=False):
        return Protocolo.objects.create(
            cartorio=self.cartorio,
            numero=numero,
            natureza=self.natureza,
            peso_dias=peso_protocolo(self.natureza, 1, 1),
            urgente=urgente,
        )

    def test_em_ferias_bloqueia_novos_protocolos(self):
        hoje = date.today()
        Ferias.objects.create(cartorio=self.cartorio, escrevente=self.ana, inicio=hoje, fim=hoje + timedelta(days=5))

        protocolo = self._protocolo("1")
        escolhido = escolher_escrevente(protocolo)

        self.assertEqual(escolhido, self.bruno)

    def test_fora_do_periodo_de_ferias_nao_bloqueia(self):
        inicio = date.today() + timedelta(days=30)
        Ferias.objects.create(cartorio=self.cartorio, escrevente=self.ana, inicio=inicio, fim=inicio + timedelta(days=5))

        protocolo = self._protocolo("1")
        escolhido = escolher_escrevente(protocolo)

        # ninguem esta de ferias agora, entao o escolhido e so quem tem menor carga (os dois em 0 -> primeiro da lista)
        self.assertEqual(escolhido, self.ana)

    def test_grupo_inteiro_de_ferias_nao_trava_a_distribuicao(self):
        hoje = date.today()
        Ferias.objects.create(cartorio=self.cartorio, escrevente=self.ana, inicio=hoje, fim=hoje + timedelta(days=5))
        Ferias.objects.create(cartorio=self.cartorio, escrevente=self.bruno, inicio=hoje, fim=hoje + timedelta(days=5))

        protocolo = self._protocolo("1")
        # nao deve levantar erro -- a regra de ferias e ignorada como rede de seguranca
        escolhido = escolher_escrevente(protocolo)
        self.assertIn(escolhido, [self.ana, self.bruno])

    def test_rodizio_de_urgentes_nao_repete_pessoa_antes_de_todo_mundo_receber(self):
        p1 = self._protocolo("1", urgente=True)
        escolhido1 = escolher_escrevente(p1)
        p1.escrevente_responsavel = escolhido1
        p1.save()

        p2 = self._protocolo("2", urgente=True)
        escolhido2 = escolher_escrevente(p2)

        self.assertNotEqual(escolhido1, escolhido2)

    def test_rodizio_de_urgentes_reseta_depois_que_todo_mundo_recebeu(self):
        p1 = self._protocolo("1", urgente=True)
        p1.escrevente_responsavel = escolher_escrevente(p1)
        p1.save()

        p2 = self._protocolo("2", urgente=True)
        escolhido2 = escolher_escrevente(p2)
        p2.escrevente_responsavel = escolhido2
        p2.save()

        # agora os dois (Ana e Bruno) ja receberam um urgente -- a rodada reseta
        # e o terceiro urgente pode ir para qualquer um dos dois de novo.
        p3 = self._protocolo("3", urgente=True)
        escolhido3 = escolher_escrevente(p3)
        self.assertIn(escolhido3, [self.ana, self.bruno])

    def test_rodizio_funciona_com_janela_de_historico_limitada(self):
        # _recebidos_rodada_atual so olha os N urgentes mais recentes (ver
        # _LIMITE_HISTORICO_RODADA), para a consulta nao crescer sem limite
        # com o historico do cartorio. Com a janela reduzida para 2, o
        # rodizio ainda precisa dar o mesmo resultado dos testes acima.
        with patch.object(distribuicao, "_LIMITE_HISTORICO_RODADA", 2):
            p1 = self._protocolo("1", urgente=True)
            p1.escrevente_responsavel = escolher_escrevente(p1)
            p1.save()

            p2 = self._protocolo("2", urgente=True)
            p2.escrevente_responsavel = escolher_escrevente(p2)
            p2.save()

            self.assertNotEqual(p1.escrevente_responsavel, p2.escrevente_responsavel)

            p3 = self._protocolo("3", urgente=True)
            escolhido3 = escolher_escrevente(p3)
            self.assertIn(escolhido3, [self.ana, self.bruno])


class ProporcaoDistribuicaoTests(TestCase):
    """Grupo.modo_distribuicao == MODO_PROPORCAO: distribuicao por cota
    fixa (CotaDistribuicao), em vez de menor carga."""

    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Proporcao", "admin_proporcao_teste")
        self.jana = Escrevente.objects.create(cartorio=self.cartorio, nome="Jana")
        self.pamela = Escrevente.objects.create(cartorio=self.cartorio, nome="Pamela")
        self.grupo = Grupo.objects.create(
            cartorio=self.cartorio, nome="Complexo", modo_distribuicao=Grupo.MODO_PROPORCAO
        )
        self.grupo.escreventes.set([self.jana, self.pamela])
        self.natureza = Natureza.objects.create(
            cartorio=self.cartorio, nome="Requerimento", grupo=self.grupo, peso_base_dias=3
        )

    def _lancar(self, numero):
        protocolo = Protocolo.objects.create(
            cartorio=self.cartorio, numero=numero, natureza=self.natureza, peso_dias=peso_protocolo(self.natureza, 1, 1)
        )
        distribuicao.distribuir(protocolo)
        return protocolo.escrevente_responsavel

    def test_sem_cotas_cadastradas_e_round_robin_simples(self):
        # Sem CotaDistribuicao, todo mundo tem cota 1 (default) -- vira
        # um rodizio simples, alternando por ordem de id.
        escolhidos = [self._lancar(str(i)) for i in range(4)]
        self.assertEqual(escolhidos, [self.jana, self.pamela, self.jana, self.pamela])

    def test_cotas_configuradas_convergem_para_a_proporcao(self):
        CotaDistribuicao.objects.create(cartorio=self.cartorio, grupo=self.grupo, escrevente=self.jana, cota=2)
        CotaDistribuicao.objects.create(cartorio=self.cartorio, grupo=self.grupo, escrevente=self.pamela, cota=3)

        escolhidos = [self._lancar(str(i)) for i in range(5)]

        self.assertEqual(
            escolhidos, [self.jana, self.pamela, self.pamela, self.jana, self.pamela]
        )
        self.assertEqual(escolhidos.count(self.jana), 2)
        self.assertEqual(escolhidos.count(self.pamela), 3)

    def test_quem_nao_tem_cota_cadastrada_usa_cota_1(self):
        # So a Pamela tem cota explicita (5); a Jana usa o default (1).
        # A proporcao final (recebidos/cota) deve seguir 1:5 -- a Pamela
        # recebe bem mais, ja que sua cota maior demora mais pra "pesar".
        CotaDistribuicao.objects.create(cartorio=self.cartorio, grupo=self.grupo, escrevente=self.pamela, cota=5)

        escolhidos = [self._lancar(str(i)) for i in range(6)]

        self.assertEqual(escolhidos.count(self.jana), 1)
        self.assertEqual(escolhidos.count(self.pamela), 5)


class CorCargaTests(TestCase):
    def test_fracao_zero_e_verde(self):
        self.assertEqual(distribuicao.cor_carga(0), "hsl(140, 55%, 40%)")

    def test_fracao_um_e_vermelho(self):
        self.assertEqual(distribuicao.cor_carga(1), "hsl(0, 55%, 40%)")

    def test_fracao_acima_de_um_continua_vermelho_nao_estoura(self):
        self.assertEqual(distribuicao.cor_carga(2.5), "hsl(0, 55%, 40%)")

    def test_fracao_meio_fica_no_meio_do_gradiente(self):
        self.assertEqual(distribuicao.cor_carga(0.5), "hsl(70, 55%, 40%)")


class IsolamentoEntreCartoriosTests(TestCase):
    """Garante que um cartorio nunca ve dados de outro -- isso e o
    requisito de seguranca mais importante de um SaaS multi-tenant."""

    def setUp(self):
        self.cartorio_a, self.user_a = _criar_tenant("Cartorio A", "admin_a_teste")
        self.cartorio_b, self.user_b = _criar_tenant("Cartorio B", "admin_b_teste")

        self.escrevente_a = Escrevente.objects.create(cartorio=self.cartorio_a, nome="Escrevente A")
        self.escrevente_b = Escrevente.objects.create(cartorio=self.cartorio_b, nome="Escrevente B")

        self.grupo_a = Grupo.objects.create(cartorio=self.cartorio_a, nome="Simples")
        self.grupo_a.escreventes.add(self.escrevente_a)
        grupo_b = Grupo.objects.create(cartorio=self.cartorio_b, nome="Simples")
        grupo_b.escreventes.add(self.escrevente_b)

        self.natureza_a = Natureza.objects.create(
            cartorio=self.cartorio_a, nome="Natureza A", grupo=self.grupo_a, peso_base_dias=3
        )
        Natureza.objects.create(cartorio=self.cartorio_b, nome="Natureza B", grupo=grupo_b, peso_base_dias=3)

        Protocolo.objects.create(
            cartorio=self.cartorio_a,
            numero="A-1",
            natureza=self.natureza_a,
            peso_dias=3,
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

    def test_ferias_so_lista_escreventes_do_proprio_cartorio(self):
        client = Client()
        client.login(username="admin_b_teste", password="SenhaForte123")

        resposta = client.get(reverse("ferias"))

        self.assertNotContains(resposta, "Escrevente A")

    def test_historico_so_lista_protocolos_do_proprio_cartorio(self):
        client = Client()
        client.login(username="admin_b_teste", password="SenhaForte123")

        resposta = client.get(reverse("historico"))

        self.assertNotContains(resposta, "A-1")

    def test_cota_distribuicao_inline_so_lista_escreventes_do_proprio_cartorio(self):
        client = Client()
        client.login(username="admin_a_teste", password="SenhaForte123")

        resposta = client.get(reverse("admin:nucleo_grupo_change", args=[self.grupo_a.id]))

        self.assertNotContains(resposta, "Escrevente B")


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

    def test_carta_de_adjudicacao_e_simples_mas_tem_alternativa_complexo(self):
        cartorio = Cartorio.objects.create(nome="Cartorio Carta")
        carregar_catalogo_padrao(cartorio)

        carta = Natureza.objects.get(cartorio=cartorio, nome="Carta de Adjudicação")
        self.assertEqual(carta.grupo.nome, "Simples")
        self.assertEqual(carta.grupo_se_inventario.nome, "Complexo")

    def test_pesos_extras_sao_carregados_por_grupo(self):
        cartorio = Cartorio.objects.create(nome="Cartorio Pesos")
        carregar_catalogo_padrao(cartorio)

        simples = Grupo.objects.get(cartorio=cartorio, nome="Simples")
        self.assertEqual(simples.peso_extra_matricula_dias, 0.5)
        self.assertEqual(simples.peso_extra_parte_dias, 0.2)

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
        self.grupo = Grupo.objects.create(
            cartorio=self.cartorio, nome="Simples", peso_extra_matricula_dias=0.5, peso_extra_parte_dias=0.2
        )
        self.grupo.escreventes.add(self.escrevente)
        self.natureza = Natureza.objects.create(
            cartorio=self.cartorio, nome="Doação", grupo=self.grupo, peso_base_dias=3
        )
        self.client = Client()
        self.client.login(username="admin_view_teste", password="SenhaForte123")

    def _payload(self, **overrides):
        payload = {"numero": "123", "natureza": self.natureza.pk, "matriculas": "1", "partes": "1", "urgente": ""}
        payload.update(overrides)
        return payload

    def test_lancar_protocolo_distribui_e_redireciona(self):
        resposta = self.client.post(reverse("lancar_protocolo"), self._payload())
        self.assertRedirects(resposta, reverse("dashboard"))

        protocolo = Protocolo.objects.get(cartorio=self.cartorio, numero="123")
        self.assertEqual(protocolo.escrevente_responsavel, self.escrevente)
        self.assertEqual(protocolo.peso_dias, 3.0)
        self.assertEqual(protocolo.status, Protocolo.STATUS_ABERTO)

    def test_peso_considera_matriculas_e_partes_extras(self):
        self.client.post(reverse("lancar_protocolo"), self._payload(matriculas="3", partes="2"))

        protocolo = Protocolo.objects.get(cartorio=self.cartorio, numero="123")
        # 3 + 0.5*(3-1) + 0.2*(2-1) = 4.2
        self.assertEqual(protocolo.peso_dias, 4.2)
        self.assertEqual(protocolo.matriculas, 3)
        self.assertEqual(protocolo.partes, 2)

    def test_inventario_marcado_usa_pesos_do_grupo_alternativo(self):
        grupo_complexo = Grupo.objects.create(
            cartorio=self.cartorio, nome="Complexo", peso_extra_matricula_dias=1.0, peso_extra_parte_dias=0.4
        )
        grupo_complexo.escreventes.add(self.escrevente)
        carta = Natureza.objects.create(
            cartorio=self.cartorio,
            nome="Carta de Adjudicação",
            grupo=self.grupo,
            grupo_se_inventario=grupo_complexo,
            peso_base_dias=3,
        )

        self.client.post(
            reverse("lancar_protocolo"),
            self._payload(natureza=carta.pk, inventario="on", matriculas="2"),
        )

        protocolo = Protocolo.objects.get(cartorio=self.cartorio, numero="123")
        # usa peso_extra_matricula_dias do grupo Complexo (1.0), nao do Simples (0.5)
        self.assertEqual(protocolo.peso_dias, 4.0)

    def test_dashboard_mostra_chip_de_copiar_apos_distribuir(self):
        self.client.post(reverse("lancar_protocolo"), self._payload())

        resposta = self.client.get(reverse("dashboard"))
        hoje = timezone.localtime(timezone.now()).strftime("%d/%m")

        self.assertContains(resposta, f"cadastrado em {hoje} - mesa de Única")
        self.assertContains(resposta, "data-copiar=")

    def test_chip_de_copiar_some_depois_de_uma_visita(self):
        self.client.post(reverse("lancar_protocolo"), self._payload())
        self.client.get(reverse("dashboard"))

        resposta = self.client.get(reverse("dashboard"))

        self.assertNotContains(resposta, "data-copiar=")

    def test_numero_duplicado_mostra_erro_sem_quebrar(self):
        self.client.post(reverse("lancar_protocolo"), self._payload())
        resposta = self.client.post(reverse("lancar_protocolo"), self._payload())

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Já existe um protocolo com esse número.")

    def test_natureza_invalida_mostra_erro_sem_quebrar(self):
        resposta = self.client.post(reverse("lancar_protocolo"), self._payload(natureza="99999"))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "escolha válida")
        self.assertFalse(Protocolo.objects.filter(cartorio=self.cartorio, numero="123").exists())

    def test_natureza_de_outro_cartorio_e_rejeitada(self):
        outro_cartorio, _ = _criar_tenant("Cartorio Outro", "admin_outro_teste")
        outro_grupo = Grupo.objects.create(cartorio=outro_cartorio, nome="Simples")
        natureza_de_outro = Natureza.objects.create(
            cartorio=outro_cartorio, nome="Natureza de outro cartorio", grupo=outro_grupo, peso_base_dias=3
        )

        resposta = self.client.post(reverse("lancar_protocolo"), self._payload(natureza=natureza_de_outro.pk))

        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "escolha válida")
        self.assertFalse(Protocolo.objects.filter(cartorio=self.cartorio, numero="123").exists())

    def test_select_de_natureza_agrupado_por_grupo(self):
        Natureza.objects.create(
            cartorio=self.cartorio,
            nome="Formal de Partilha - Inventário",
            grupo=Grupo.objects.create(cartorio=self.cartorio, nome="Complexo"),
            peso_base_dias=6,
        )

        resposta = self.client.get(reverse("lancar_protocolo"))

        self.assertContains(resposta, '<optgroup label="Simples">')
        self.assertContains(resposta, '<optgroup label="Complexo">')

    def test_campo_inventario_so_aparece_nos_dados_para_natureza_com_alternativa(self):
        grupo_complexo = Grupo.objects.create(cartorio=self.cartorio, nome="Complexo")
        carta = Natureza.objects.create(
            cartorio=self.cartorio,
            nome="Carta de Adjudicação",
            grupo=self.grupo,
            grupo_se_inventario=grupo_complexo,
            peso_base_dias=3,
        )

        resposta = self.client.get(reverse("lancar_protocolo"))
        conteudo = resposta.content.decode()

        self.assertIn(f'"grupoInventarioId": {grupo_complexo.id}', conteudo)
        # a natureza sem alternativa nao deve apontar pra nenhum grupo de inventario
        self.assertIn(f'"{self.natureza.id}": {{"pesoBase": 3.0, "grupoId": {self.grupo.id}, "grupoInventarioId": null}}', conteudo)


class HistoricoViewTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio Historico", "admin_historico_teste")
        self.escrevente = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana")
        grupo = Grupo.objects.create(cartorio=self.cartorio, nome="Simples")
        grupo.escreventes.add(self.escrevente)
        natureza = Natureza.objects.create(cartorio=self.cartorio, nome="Requerimento", grupo=grupo, peso_base_dias=3)
        self.protocolo = Protocolo.objects.create(
            cartorio=self.cartorio,
            numero="1",
            natureza=natureza,
            peso_dias=3,
            escrevente_responsavel=self.escrevente,
        )
        self.client = Client()
        self.client.login(username="admin_historico_teste", password="SenhaForte123")

    def test_mudar_status_para_concluido_preenche_data_conclusao_e_libera_carga(self):
        self.assertEqual(distribuicao.carga_atual_dias(self.cartorio).get(self.escrevente.id), 3.0)

        self.client.post(
            reverse("historico"), {"protocolo_id": self.protocolo.id, "status": Protocolo.STATUS_CONCLUIDO}
        )

        self.protocolo.refresh_from_db()
        self.assertEqual(self.protocolo.status, Protocolo.STATUS_CONCLUIDO)
        self.assertEqual(self.protocolo.data_conclusao, timezone.localdate())
        self.assertEqual(distribuicao.carga_atual_dias(self.cartorio).get(self.escrevente.id, 0), 0)

    def test_voltar_status_para_aberto_limpa_data_conclusao(self):
        self.protocolo.status = Protocolo.STATUS_CONCLUIDO
        self.protocolo.data_conclusao = timezone.localdate()
        self.protocolo.save()

        self.client.post(reverse("historico"), {"protocolo_id": self.protocolo.id, "status": Protocolo.STATUS_ABERTO})

        self.protocolo.refresh_from_db()
        self.assertEqual(self.protocolo.status, Protocolo.STATUS_ABERTO)
        self.assertIsNone(self.protocolo.data_conclusao)


class FeriasViewTests(TestCase):
    def setUp(self):
        self.cartorio, self.user = _criar_tenant("Cartorio FeriasView", "admin_feriasview_teste")
        self.escrevente = Escrevente.objects.create(cartorio=self.cartorio, nome="Ana")
        self.client = Client()
        self.client.login(username="admin_feriasview_teste", password="SenhaForte123")

    def test_adicionar_periodo(self):
        resposta = self.client.post(
            reverse("ferias"),
            {"escrevente": self.escrevente.id, "inicio": "2026-01-10", "fim": "2026-01-20"},
        )
        self.assertRedirects(resposta, reverse("ferias"))
        self.assertEqual(Ferias.objects.filter(cartorio=self.cartorio, escrevente=self.escrevente).count(), 1)

    def test_remover_periodo(self):
        periodo = Ferias.objects.create(
            cartorio=self.cartorio, escrevente=self.escrevente, inicio="2026-01-10", fim="2026-01-20"
        )

        self.client.post(reverse("ferias"), {"remover": periodo.id})

        self.assertFalse(Ferias.objects.filter(pk=periodo.id).exists())

    def test_nao_pode_remover_periodo_de_outro_cartorio(self):
        outro_cartorio, _ = _criar_tenant("Cartorio FeriasOutro", "admin_feriasoutro_teste")
        outro_escrevente = Escrevente.objects.create(cartorio=outro_cartorio, nome="Bruno")
        periodo_de_outro = Ferias.objects.create(
            cartorio=outro_cartorio, escrevente=outro_escrevente, inicio="2026-01-10", fim="2026-01-20"
        )

        self.client.post(reverse("ferias"), {"remover": periodo_de_outro.id})

        self.assertTrue(Ferias.objects.filter(pk=periodo_de_outro.id).exists())


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
        natureza = Natureza.objects.create(cartorio=self.cartorio, nome="Doação", grupo=grupo, peso_base_dias=3)
        Protocolo.objects.create(cartorio=self.cartorio, numero="1", natureza=natureza, peso_dias=3)
        Protocolo.objects.create(cartorio=self.cartorio, numero="2", natureza=natureza, peso_dias=3, urgente=True)

    def test_protocolo_urgente_aparece_antes_na_lista_mesmo_sendo_mais_antigo(self):
        client = Client()
        client.login(username="admin_urgente_teste", password="SenhaForte123")

        resposta = client.get(reverse("dashboard"))

        posicao_urgente = resposta.content.decode().find(">2 <span")
        posicao_normal = resposta.content.decode().find(">1</td>")
        self.assertNotEqual(posicao_urgente, -1)
        self.assertNotEqual(posicao_normal, -1)
        self.assertLess(posicao_urgente, posicao_normal)


class RecuperacaoDeSenhaTests(TestCase):
    """django.contrib.admin tem suas proprias registration/password_reset_*.html
    (mesmos nomes de arquivo) e vem antes de "nucleo" no INSTALLED_APPS --
    sem os nossos templates estarem em saas/templates/ (checado antes de
    qualquer app), o admin vence e a tela de recuperacao fica com a cara
    padrao do Django em vez da nossa."""

    def setUp(self):
        _criar_tenant("Cartorio Senha", "admin_senha_teste")

    def test_login_mostra_link_esqueceu_a_senha(self):
        resposta = Client().get(reverse("login"))
        self.assertContains(resposta, "Esqueceu a senha?")

    def test_tela_recuperar_senha_usa_o_nosso_template_no_do_admin(self):
        resposta = Client().get(reverse("password_reset"))
        self.assertContains(resposta, "Enviar link de recuperação")
