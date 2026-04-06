# Kadu Farias
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from domain.schemas.ClienteSchema import ClienteCreate, ClienteUpdate, ClienteResponse
from domain.schemas.AuthSchema import FuncionarioAuth
from infra.orm.ClienteModel import ClienteDB
from infra.database import get_db
from infra.dependencies import get_current_active_user, require_group

router = APIRouter()

@router.get("/cliente/", response_model=List[ClienteResponse], tags=["Cliente"])
async def get_clientes(
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    return db.query(ClienteDB).all()

@router.get("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"])
async def get_cliente_by_id(
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(get_current_active_user)
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id_cliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    return cliente

@router.post("/cliente/", response_model=ClienteResponse, status_code=status.HTTP_201_CREATED, tags=["Cliente"])
async def post_cliente(
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
    return novo

@router.put("/cliente/{id}", response_model=ClienteResponse, tags=["Cliente"])
async def put_cliente(
    id: int,
    data: ClienteUpdate,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id_cliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cliente, key, value)
    db.commit()
    db.refresh(cliente)
    return cliente

@router.delete("/cliente/{id}", status_code=204, tags=["Cliente"])
async def delete_cliente(
    id: int,
    db: Session = Depends(get_db),
    current_user: FuncionarioAuth = Depends(require_group([1]))
):
    cliente = db.query(ClienteDB).filter(ClienteDB.id_cliente == id).first()
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    db.delete(cliente)
    db.commit()