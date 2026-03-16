from infra import database
from sqlalchemy import Column, VARCHAR, Integer, DECIMAL, BLOB

class ProdutoDB(database.Base):
    __tablename__ = 'tb_produto'

    id_produto = Column(Integer, primary_key=True, autoincrement=True, index=True)
    nome = Column(VARCHAR(100), nullable=False)
    descricao = Column(VARCHAR(200))
    foto = Column(BLOB)
    valor_unitario = Column(DECIMAL(11, 2), nullable=False)

    def __init__(self, nome, descricao, foto, valor_unitario, id_produto=None):
        self.id_produto = id_produto
        self.nome = nome
        self.descricao = descricao
        self.foto = foto
        self.valor_unitario = valor_unitario