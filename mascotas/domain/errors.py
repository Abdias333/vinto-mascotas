class DominioError(Exception):
    """Base de los errores de negocio (se muestran tal cual al usuario)."""


class ValidacionError(DominioError):
    pass


class TransicionInvalida(DominioError):
    pass


class PermisoDenegado(DominioError):
    pass


class NoEncontrado(DominioError):
    pass


class CredencialesInvalidas(DominioError):
    pass
