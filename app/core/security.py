from passlib.context import CryptContext

password_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

#Valida a força da senha. 
def validate_password_strength(password: str) -> str:
    if len(password) < 8:
        raise ValueError("A senha deve ter pelo menos 8 caracteres")
    if not any(c.isupper() for c in password):
        raise ValueError("A senha deve conter ao menos uma letra maiúscula")
    if not any(c.islower() for c in password):
        raise ValueError("A senha deve conter ao menos uma letra minúscula")
    if not any(c.isdigit() for c in password):
        raise ValueError("A senha deve conter ao menos um número")
    if not any(c in "!@#$%^&*()-_=+[{]}\|;:'\",<.>/?`~" for c in password):
        raise ValueError("A senha deve conter ao menos um caractere especial")
    return password

#hash e verificação de senha usando passlib
def hash_password(password: str) -> str:
    return password_context.hash(password)

#verifica se a senha fornecida corresponde ao hash armazenado
def verify_password(password: str, hashed_password:str) -> bool:
    return password_context.verify(password, hashed_password)