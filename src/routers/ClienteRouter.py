# Kadu Farias
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from typing import List

from domain.schemas.ClienteSchema import ClienteCreate, ClienteUpdate, ClienteResponse
from domain.schemas.AuthSchema import FuncionarioAuth

from infra.orm.ClienteModel import ClienteDB
from infra.database import get_db
from infra.dependencies import get_current_active_user, require_group
from infra.rate_limit import limiter, get_rate_limit
from services.AuditoriaService import AuditoriaService

router = APIRouter()


@router.get("/cliente/", response_model=List[ClienteResponse], tags=["Cliente"])
@limiter.limit(get_rate_limit("moderate"))
async def get_clientes(
    request: Request,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    return db.query(ClienteDB).all()


@router.get("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"])
@limiter.limit(get_rate_limit("moderate"))
async def get_cliente_by_id(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id_cliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente


@router.post("/cliente/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED, tags=["Cliente"])
@limiter.limit(get_rate_limit("restrictive"))
async def post_cliente(
    request: Request,
    data: ClienteCreate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    if db.query(ClienteDB).filter(ClienteDB.cpf == data.cpf).first():
        raise HTTPException(status_code=400, detail="CPF já cadastrado")

    novo = ClienteDB(id_cliente=None, **data.model_dump())
    db.add(novo)
    db.commit()
    db.refresh(novo)

    AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="CREATE",
        recurso="CLIENTE",
        recurso_id=novo.id_cliente,
        dados_antigos=None,
        dados_novos=novo,
        request=request
    )

    return novo


@router.put("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"])
@limiter.limit(get_rate_limit("restrictive"))
async def put_cliente(
    request: Request,
    id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id_cliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    dados_antigos_obj = cliente.__dict__.copy()

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cliente, key, value)

    db.commit()
    db.refresh(cliente)

    AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="UPDATE",
        recurso="CLIENTE",
        recurso_id=cliente.id_cliente,
        dados_antigos=dados_antigos_obj,
        dados_novos=cliente,
        request=request
    )

    return cliente


@router.delete("/cliente/{id}", status_code=204, tags=["Cliente"])
@limiter.limit(get_rate_limit("critical"))
async def delete_cliente(
    request: Request,
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id_cliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")

    dados_antigos_obj = cliente.__dict__.copy()

    db.delete(cliente)
    db.commit()

    AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="DELETE",
        recurso="CLIENTE",
        recurso_id=id,
        dados_antigos=dados_antigos_obj,
        dados_novos=None,
        request=request
    )