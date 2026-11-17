"""Regras de negócio puras para gestão operacional de demandas."""
from datetime import datetime, timedelta, timezone

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


def situacao_prazo(status: str, prazo: datetime | None, *, agora: datetime | None = None) -> str:
    if status in {"resolvida", "cancelada"}:
        return "encerrada"
    if prazo is None:
        return "sem_prazo"
    if prazo.tzinfo is None or prazo.utcoffset() is None:
        raise RegraNegocioError("Prazo precisa de fuso horário")
    agora = agora or datetime.now(timezone.utc)
    if prazo < agora:
        return "atrasada"
    if prazo <= agora + timedelta(hours=24):
        return "proximo_vencimento"
    return "em_dia"


def normalizar_prazo(valor: str | None) -> datetime | None:
    if valor is None or valor == "":
        return None
    try:
        dt = datetime.fromisoformat(valor.replace("Z", "+00:00"))
    except (ValueError, TypeError) as exc:
        raise RegraNegocioError("Prazo inválido; use ISO 8601 com fuso") from exc
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise RegraNegocioError("Prazo sem fuso horário")
    return dt.astimezone(timezone.utc)
