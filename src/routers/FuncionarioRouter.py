#Kadu Farias
from fastapi import APIRouter, Depends, HTTPException, status, Request
from services.AuditoriaService import AuditoriaService
from infra.rate_limit import limiter, get_rate_limit
from slowapi.errors import RateLimitExceeded
from sqlalchemy.orm import Session
from typing import List

# Domain Schemas
from domain.schemas.FuncionarioSchema import (
    FuncionarioCreate,
    FuncionarioUpdate,
    FuncionarioResponse
)
from domain.schemas.AuthSchema import FuncionarioAuth

# Infra
from infra.orm.FuncionarioModel import FuncionarioDB
from infra.database import get_db
from infra.security import get_password_hash
from infra.dependencies import get_current_active_user, require_group

router = APIRouter()

@router.get("/funcionario/", response_model=List[FuncionarioResponse], tags=["Funcionário"], status_code=status.HTTP_200_OK)
@limiter.limit(get_rate_limit("moderate"))
async def get_funcionarios_all(request: Request, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(require_group([1]))): # Mudei o nome para evitar conflito
    """Retorna todos os funcionários"""
    try:
        funcionarios = db.query(FuncionarioDB).all()
        return funcionarios
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionários: {str(e)}"
        )   

@router.get("/funcionario/{id}", response_model=FuncionarioResponse, tags=["Funcionário"], status_code=status.HTTP_200_OK)
@limiter.limit(get_rate_limit("critical"))
async def get_funcionario_by_id(request: Request, id: int, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(get_current_active_user)): # Mudei o nome para evitar conflito
    """Retorna um funcionário específico pelo ID"""
    try:
        # CORREÇÃO AQUI: De .id para .id_funcionario
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id_funcionario == id).first()
        
        if not funcionario:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Funcionário não encontrado")

        return funcionario
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Erro ao buscar funcionário: {str(e)}"
        )

@router.post("/funcionario/", response_model=FuncionarioResponse, status_code=status.HTTP_201_CREATED, tags=["Funcionário"])
async def post_funcionario(funcionario_data: FuncionarioCreate, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(require_group([1]))):
    """Cria um novo funcionário"""
    try:
        existing_funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == funcionario_data.cpf).first()

        if existing_funcionario:
             raise HTTPException(
                 status_code=status.HTTP_400_BAD_REQUEST, detail="Já existe um funcionário com este CPF"
             )
        
        # Hash da senha (movido para dentro do try ou logo acima dele)
        hashed_password = get_password_hash(funcionario_data.senha)

        novo_funcionario = FuncionarioDB(
            id_funcionario=None,
            nome=funcionario_data.nome,
            matricula=funcionario_data.matricula,
            cpf=funcionario_data.cpf,
            telefone=funcionario_data.telefone,
            grupo=funcionario_data.grupo,
            senha=hashed_password # Usando a senha criptografada
        )

        db.add(novo_funcionario)
        db.commit()
        db.refresh(novo_funcionario)
        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
                db=db,
                funcionario_id=current_user.id,
                acao="CREATE",
                recurso="FUNCIONARIO",
                recurso_id=novo_funcionario.id,
                dados_antigos=None,
                dados_novos=novo_funcionario, # Objeto SQLAlchemy com dados novos
                request=request # Request completo para capturar IP e user agent
            )

        return novo_funcionario

    except Exception as e:
        # Aqui você fecha o bloco try que estava aberto!
        db.rollback() # Boa prática: desfazer mudanças se der erro
        raise HTTPException(status_code=500, detail=f"Erro interno: {str(e)}")

@router.put("/funcionario/{id}", response_model=FuncionarioResponse, tags=["Funcionário"], status_code=status.HTTP_200_OK)
async def put_funcionario(id: int, funcionario_data: FuncionarioUpdate, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(require_group([1]))):
    """Atualiza um funcionário existente"""
    try:
        # CORREÇÃO AQUI: De .id para .id_funcionario
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id_funcionario == id).first()
        
        if not funcionario:
            raise HTTPException(status_code=404, detail="Funcionário não encontrado")

        if funcionario_data.cpf and funcionario_data.cpf != funcionario.cpf:
            existing = db.query(FuncionarioDB).filter(FuncionarioDB.cpf == funcionario_data.cpf).first()
            if existing:
                raise HTTPException(status_code=400, detail="CPF já cadastrado")

        # armazena uma copia do objeto com os dados atuais, para salvar na auditoria
        # não pode manter referencia com funcionário, para que o auditoria possa comparar
        # por isso a cópia do __dict__
        dados_antigos_obj = funcionario.__dict__.copy()

        # Hash da senha se fornecida nova senha
        if funcionario_data.senha:
            funcionario_data.senha = get_password_hash(funcionario_data.senha)       

        update_data = funcionario_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(funcionario, field, value)

        db.commit()
        db.refresh(funcionario)
       
        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="UPDATE",
        recurso="FUNCIONARIO",
        recurso_id=funcionario.id,
        dados_antigos=dados_antigos_obj, # Objeto SQLAlchemy com dados antigos
        dados_novos=funcionario, # Objeto SQLAlchemy com dados novos
        request=request # Request completo para capturar IP e user agent
        )
        
        return funcionario

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/funcionario/{id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Funcionário"])
async def delete_funcionario(id: int, db: Session = Depends(get_db), current_user: FuncionarioAuth = Depends(require_group([1]))):
    """Remove um funcionário"""
    try:
        # CORREÇÃO AQUI: De .id para .id_funcionario
        funcionario = db.query(FuncionarioDB).filter(FuncionarioDB.id_funcionario == id).first()

        if not funcionario:
            raise HTTPException(status_code=404, detail="Funcionário não encontrado")

        db.delete(funcionario)
        db.commit()

        # Depois de tudo executado e antes do return, registra a ação na auditoria
        AuditoriaService.registrar_acao(
        db=db,
        funcionario_id=current_user.id,
        acao="DELETE",
        recurso="FUNCIONARIO",
        recurso_id=funcionario.id,
        dados_antigos=funcionario,
        dados_novos=None,
        request=request
        )
        
        return None
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))