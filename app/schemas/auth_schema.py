from pydantic import EmailStr
from app.schemas.base_schema import BaseSchema

# Request da rota de login — email e senha do usuário.
class LoginRequest(BaseSchema):
    email: EmailStr
    password: str

# Resposta da rota de login — token do do usuário.
class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = "Bearer"

# Request da rota de refresh — apenas o refresh_token.
class RefreshTokenRequest(BaseSchema):
    refresh_token: str

#Resposta da rota de refresh — apenas um novo access_token.
class AccessTokenResponse(BaseSchema):
   

    access_token: str
    token_type: str = "Bearer"