from datetime import datetime, timedelta, timezone
import pytest
from fj_operacional.domain import (
    validar_transicao, situacao_prazo, normalizar_prazo,
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
    assert situacao_prazo("em_andamento", now-timedelta(minutes=1), agora=now) == "atrasada"
    assert situacao_prazo("resolvida", now-timedelta(days=2), agora=now) == "encerrada"
    assert situacao_prazo("nova", None, agora=now) == "sem_prazo"


def test_prazo_rejeita_data_sem_fuso():
    with pytest.raises(RegraNegocioError):
        normalizar_prazo("2026-11-17T10:00:00")
    assert normalizar_prazo("2026-11-17T10:00:00-03:00").hour == 13
