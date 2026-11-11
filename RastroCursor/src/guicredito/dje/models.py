from pydantic import BaseModel, Field


class Parte(BaseModel):
    papel: str
    nome: str


class Advogado(BaseModel):
    nome: str = ""
    oab: str = ""


class Publicacao(BaseModel):
    data: str
    caderno: str
    pagina: int
    cnj: str
    vara: str | None = None
    texto: str
    partes: list[Parte] = Field(default_factory=list)
    nomes: list[str] = Field(default_factory=list)
    advogados: list[Advogado] = Field(default_factory=list)
    sinais: list[str] = Field(default_factory=list)
