from datetime import datetime, timedelta, timezone
import pytest
from fj_operacional.domain import (
    validar_transicao, situacao_prazo, normalizar_prazo, prazo_atrasado, data_prazo,
    RegraNegocioError, SemPermissaoError,
)


def test_status_nao_pula_validacao():
    with pytest.raises(RegraNegocioError):
        validar_transicao("pendente", "resolvida", "gestor", "OK")


def test_operador_nao_valida_conclusao():
    with pytest.raises(SemPermissaoError):
        validar_transicao("aguardando_validacao", "resolvida", "operador", "Validado")


def test_operador_pode_assumir():
    validar_transicao("pendente", "em_andamento", "operador", "")


def test_cancelamento_precisa_justificativa():
    with pytest.raises(RegraNegocioError):
        validar_transicao("nova", "cancelada", "gestor", "  ")


def test_reabertura_exige_gestor_e_justificativa():
    with pytest.raises(SemPermissaoError):
        validar_transicao("resolvida", "em_andamento", "operador", "Problema persiste")
    with pytest.raises(RegraNegocioError):
        validar_transicao("resolvida", "em_andamento", "gestor", "")
    validar_transicao("resolvida", "em_andamento", "gestor", "Problema persiste")


def test_prazo_separado_do_status():
    now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
    assert situacao_prazo("pendente", now+timedelta(hours=40), agora=now) == "em_dia"
    assert situacao_prazo("pendente", now+timedelta(hours=10), agora=now) == "proximo_vencimento"
    assert situacao_prazo("em_andamento", now-timedelta(minutes=1), agora=now) == "proximo_vencimento"
    assert situacao_prazo("em_andamento", now-timedelta(days=1), agora=now) == "atrasada"
    assert situacao_prazo("resolvida", now-timedelta(days=2), agora=now) == "encerrada"
    assert situacao_prazo("nova", None, agora=now) == "sem_prazo"


def test_prazo_rejeita_data_sem_fuso():
    with pytest.raises(RegraNegocioError):
        normalizar_prazo("2026-11-17T10:00:00")
    assert normalizar_prazo("2026-11-17T10:00:00-03:00").hour == 13

def test_prazo_vencido_no_dia_seguinte_sem_horario():
    # Horário de São Paulo: vencimento só muda após o dia civil terminar.
    hoje = datetime(2026, 11, 18, 12, tzinfo=timezone.utc)
    prazo_ontem = normalizar_prazo("17/11/2026")
    prazo_hoje = normalizar_prazo("18/11/2026")
    assert data_prazo(prazo_ontem).strftime("%d/%m/%Y") == "17/11/2026"
    assert prazo_atrasado("em_andamento", prazo_ontem, agora=hoje)
    assert situacao_prazo("em_andamento", prazo_ontem, agora=hoje) == "atrasada"
    assert not prazo_atrasado("em_andamento", prazo_hoje, agora=hoje)
    assert not prazo_atrasado("resolvida", prazo_ontem, agora=hoje)
    assert not prazo_atrasado("cancelada", prazo_ontem, agora=hoje)


def test_prazo_valido_em_portugues_e_rejeita_data_invalida():
    assert normalizar_prazo("29/02/2028") is not None
    for entrada in ("31/02/2026", "11/18/2026", "31/13/2026"):
        with pytest.raises(RegraNegocioError):
            normalizar_prazo(entrada)


def test_fronteira_virada_dia_sao_paulo():
    prazo = normalizar_prazo("17/11/2026")
    assert not prazo_atrasado("pendente",prazo,
      agora=datetime.fromisoformat("2026-11-17T23:59:59-03:00"))
    assert prazo_atrasado("pendente",prazo,
      agora=datetime.fromisoformat("2026-11-18T00:00:00-03:00"))
