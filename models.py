from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, Date
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class Usuario(Base):
    """
    Armazena as configurações globais e metas financeiras do usuário.
    Estes dados alimentam os cálculos do Dashboard e do Smart Rebalance.
    """
    __tablename__ = 'usuario'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50), default="Master User")
    valor_hora = Column(Float, default=85.0)
    horas_dia = Column(Float, default=8.0)
    reserva_meses = Column(Integer, default=6) # Quantos meses de custo fixo deseja na reserva
    
    # Metas de Alocação de Ativos (%)
    meta_acoes = Column(Float, default=30.0)
    meta_fiis = Column(Float, default=20.0)
    meta_rf = Column(Float, default=30.0)
    meta_acoes_us = Column(Float, default=15.0) # Exposição em Dólar
    meta_crypto = Column(Float, default=5.0)
    
    # Limites de Gastos Saudáveis (%)
    limite_essencial = Column(Float, default=50.0)
    limite_lifestyle = Column(Float, default=30.0)

class Transacao(Base):
    """
    O Livro Caixa. Registra cada centavo que entra ou sai.
    A 'natureza' separa o que é sobrevivência (Essencial) do que é conforto (Estilo de Vida).
    """
    __tablename__ = 'transacoes'
    id = Column(Integer, primary_key=True)
    data = Column(Date)
    mes_ano = Column(String(7)) # Formato MM/YYYY para facilitar os filtros mensais
    descricao = Column(String(100))
    categoria = Column(String(50))
    tipo = Column(String(20)) # Receita, Despesa
    natureza = Column(String(20)) # Essencial, Estilo de Vida, Renda Extra
    valor = Column(Float)

class Ativo(Base):
    """
    A carteira de investimentos. Guarda a quantidade e o preço médio pago.
    O preço atual é buscado em tempo real na internet (engine.py).
    """
    __tablename__ = 'ativos'
    id = Column(Integer, primary_key=True)
    ticker = Column(String(20))
    classe = Column(String(30)) # Ações BR, FIIs, Ações US, Crypto, Renda Fixa
    quantidade = Column(Float)
    preco_medio = Column(Float)
    yield_anual = Column(Float, default=0.0)

class MetaFinanceira(Base):
    """
    Sinking Funds (Envelopes). Dinheiro com nome e prazo definido.
    Ex: 'Trocar de Carro', 'Viagem Europa'.
    """
    __tablename__ = 'metas'
    id = Column(Integer, primary_key=True)
    nome = Column(String(50))
    valor_alvo = Column(Float)
    valor_atual = Column(Float, default=0.0)
    prazo = Column(Date)
    icone = Column(String(10), default="🎯")

class Recorrente(Base):
    __tablename__ = 'recorrentes'
    id = Column(Integer, primary_key=True)
    descricao = Column(String)
    valor = Column(Float)
    categoria = Column(String)
    natureza = Column(String)
    tipo_recorrencia = Column(String) # 'Fixa' ou 'Parcelada'
    total_parcelas = Column(Integer, default=999) # 999 = infinito/fixo
    mes_inicio = Column(Integer) # Mês que começou (1-12)
    ano_inicio = Column(Integer) # Ano que começou
    ativo = Column(Boolean, default=True)

def init_db():
    """
    Cria o arquivo do banco de dados SQLite caso ele não exista e retorna a sessão.
    """
    engine = create_engine('sqlite:///wealth_master.db', connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)()