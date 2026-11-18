"""Regras de negócio puras para gestão operacional de demandas."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

FUSO_OPERACIONAL = ZoneInfo('America/Sao_Paulo')

STATUS = (
    "nova", "pendente", "em_andamento", "aguardando_validacao",
    "resolvida", "cancelada",
)
ATIVOS = STATUS[:4]
PERFIS = {"operador", "gestor", "administrador"}
TRANSICOES = {
    "nova": {"pendente", "cancelada"},
    "pendente": {"em_andamento", "cancelada"},
    "em_andamento": {"aguardando_validacao", "cancelada"},
    "aguardando_validacao": {"em_andamento", "resolvida", "cancelada"},
    "resolvida": {"em_andamento"},
    "cancelada": set(),
}


class RegraNegocioError(ValueError):
    pass


class ConflitoVersaoError(RegraNegocioError):
    pass


class NaoEncontradoError(RegraNegocioError):
    pass


class SemPermissaoError(RegraNegocioError):
    pass


def validar_perfil(perfil: str) -> None:
    if perfil not in PERFIS:
        raise SemPermissaoError("Perfil não autorizado")


def validar_transicao(origem: str, destino: str, perfil: str, justificativa: str) -> None:
    validar_perfil(perfil)
    if origem not in TRANSICOES or destino not in TRANSICOES[origem]:
        raise RegraNegocioError(f"Transição não permitida: {origem} → {destino}")
    if destino in {"resolvida", "cancelada"} or origem == "resolvida":
        if perfil not in {"gestor", "administrador"}:
            raise SemPermissaoError("Somente gestor/administrador pode validar, cancelar ou reabrir")
    if destino == "pendente" and perfil not in {"gestor", "administrador"}:
        raise SemPermissaoError("Triagem exige gestor/administrador")
    if destino == "resolvida" and origem != "aguardando_validacao":
        raise RegraNegocioError("Conclusão exige validação anterior")
    if (destino in {"cancelada", "resolvida"} or origem == "resolvida") and not justificativa.strip():
        raise RegraNegocioError("Informe justificativa para conclusão, cancelamento ou reabertura")


def data_prazo(prazo: datetime | None):
    """Data civil do vencimento em São Paulo, independente do horário no servidor."""
    if prazo is None:
        return None
    if prazo.tzinfo is None or prazo.utcoffset() is None:
        raise RegraNegocioError("Prazo precisa de fuso horário")
    return prazo.astimezone(FUSO_OPERACIONAL).date()


def prazo_atrasado(status: str, prazo: datetime | None, *, agora: datetime | None = None) -> bool:
    """Vence apenas no dia SEGUINTE à data prevista, sem marcar concluídos."""
    if status in {"resolvida", "cancelada"} or prazo is None:
        return False
    agora = agora or datetime.now(timezone.utc)
    if agora.tzinfo is None or agora.utcoffset() is None:
        raise RegraNegocioError("Referência de data sem fuso horário")
    return data_prazo(prazo) < agora.astimezone(FUSO_OPERACIONAL).date()


def situacao_prazo(status: str, prazo: datetime | None, *, agora: datetime | None = None) -> str:
    if status in {"resolvida", "cancelada"}:
        return "encerrada"
    if prazo is None:
        return "sem_prazo"
    agora = agora or datetime.now(timezone.utc)
    if prazo_atrasado(status, prazo, agora=agora):
        return "atrasada"
    if data_prazo(prazo) <= agora.astimezone(FUSO_OPERACIONAL).date() + timedelta(days=1):
        return "proximo_vencimento"
    return "em_dia"


def normalizar_prazo(valor: str | None) -> datetime | None:
    if valor is None or valor == "":
        return None
    if not isinstance(valor, str):
        raise RegraNegocioError("Data prevista inválida")
    # O calendário operacional usa dia/mês/ano e considera o dia completo.
    if "/" in valor:
        try:
            dia = datetime.strptime(valor, "%d/%m/%Y")
            if dia.strftime("%d/%m/%Y") != valor:
                raise ValueError("Formato inválido")
            dt = dia.replace(hour=23, minute=59, second=59, tzinfo=FUSO_OPERACIONAL)
        except ValueError as exc:
            raise RegraNegocioError("Informe a data em dd/mm/aaaa") from exc
    else:
        # Mantém compatibilidade com registros de data/hora preexistentes.
        try:
            dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except (ValueError, TypeError) as exc:
            raise RegraNegocioError("Prazo inválido; use dd/mm/aaaa ou ISO 8601 com fuso") from exc
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise RegraNegocioError("Prazo sem fuso horário")
    return dt.astimezone(timezone.utc)
