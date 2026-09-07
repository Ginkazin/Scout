class AppError(Exception):
    """Exceção base para todos os erros de domínio da aplicação.
    Nunca deve ser lançada diretamente — use uma das subclasses abaixo."""
    pass


class NotFoundError(AppError):
    """Recurso solicitado não existe (ou não pertence ao usuário atual).
    A rota deve traduzir isso para HTTP 404."""
    pass


class ConflictError(AppError):
    """Ação conflita com um recurso já existente (ex: nome/email duplicado).
    A rota deve traduzir isso para HTTP 409."""
    pass


class UnauthorizedError(AppError):
    """Credenciais inválidas ou token expirado/malformado.
    A rota deve traduzir isso para HTTP 401."""
    pass


class PlanLimitExceededError(AppError):
    """Ação bloqueada por limite do plano de assinatura do usuário.
    A rota deve traduzir isso para HTTP 403."""
    pass