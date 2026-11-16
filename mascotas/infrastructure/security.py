import bcrypt

from mascotas.application.ports import IPasswordHasher


class BcryptHasher(IPasswordHasher):
    @staticmethod
    def _bytes(clave: str) -> bytes:
        return clave.encode("utf-8")[:72]  # límite de bcrypt

    def hashear(self, clave: str) -> str:
        return bcrypt.hashpw(self._bytes(clave), bcrypt.gensalt()).decode("ascii")

    def verificar(self, clave: str, hash_: str) -> bool:
        try:
            return bcrypt.checkpw(self._bytes(clave), hash_.encode("ascii"))
        except ValueError:
            return False
