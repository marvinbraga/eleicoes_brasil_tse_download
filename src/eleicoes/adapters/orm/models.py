"""Mapped tables for the report stores. Columns follow adapters/sql/tables.sql."""

from datetime import datetime

from sqlalchemy import DateTime, ForeignKeyConstraint, Integer, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class CorrespondenceSection(Base):
    """raw.csec has no primary key. arquivo, membro and geracao only identify rows for the ORM."""

    __tablename__ = "csec"
    __table_args__ = {"schema": "raw"}

    arquivo: Mapped[str] = mapped_column(Text, primary_key=True)
    membro: Mapped[str] = mapped_column(Text, primary_key=True)
    geracao: Mapped[str] = mapped_column(Text, primary_key=True)
    sg_uf: Mapped[str | None] = mapped_column(Text, nullable=True)
    cd_municipio: Mapped[str | None] = mapped_column(Text, nullable=True)
    nm_municipio: Mapped[str | None] = mapped_column(Text, nullable=True)


class PresidentGovernorHeader(Base):
    __tablename__ = "relatorio_presidente_governador"
    __table_args__ = {"schema": "analise"}

    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
    gerado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PresidentGovernorLine(Base):
    __tablename__ = "relatorio_presidente_governador_linha"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ano", "turno"],
            [
                "analise.relatorio_presidente_governador.ano",
                "analise.relatorio_presidente_governador.turno",
            ],
        ),
        {"schema": "analise"},
    )

    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
    uf: Mapped[str] = mapped_column(Text, primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    cargo: Mapped[str] = mapped_column(Text, primary_key=True)
    partido: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    votos_nominais: Mapped[int] = mapped_column(Integer, nullable=False)
    votos_legenda: Mapped[int] = mapped_column(Integer, nullable=False)


class PresidentGovernorBallot(Base):
    __tablename__ = "relatorio_presidente_governador_cedula"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ano", "turno"],
            [
                "analise.relatorio_presidente_governador.ano",
                "analise.relatorio_presidente_governador.turno",
            ],
        ),
        {"schema": "analise"},
    )

    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
    uf: Mapped[str] = mapped_column(Text, primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    cargo: Mapped[str] = mapped_column(Text, primary_key=True)
    branco: Mapped[int] = mapped_column(Integer, nullable=False)
    nulo: Mapped[int] = mapped_column(Integer, nullable=False)


class PowerReportHeader(Base):
    __tablename__ = "relatorio_poder"
    __table_args__ = {"schema": "analise"}

    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo: Mapped[str] = mapped_column(Text, primary_key=True)
    gerado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PowerReportLine(Base):
    __tablename__ = "relatorio_poder_linha"
    __table_args__ = (
        ForeignKeyConstraint(
            ["ano", "turno", "cargo"],
            [
                "analise.relatorio_poder.ano",
                "analise.relatorio_poder.turno",
                "analise.relatorio_poder.cargo",
            ],
        ),
        {"schema": "analise"},
    )

    ano: Mapped[int] = mapped_column(Integer, primary_key=True)
    turno: Mapped[int] = mapped_column(Integer, primary_key=True)
    cargo: Mapped[str] = mapped_column(Text, primary_key=True)
    nivel: Mapped[str] = mapped_column(Text, primary_key=True)
    codigo: Mapped[str] = mapped_column(Text, primary_key=True)
    partido: Mapped[int] = mapped_column(Integer, primary_key=True)
    nome: Mapped[str] = mapped_column(Text, nullable=False)
    comparecimento: Mapped[int] = mapped_column(Integer, nullable=False)
    votos_nominais: Mapped[int] = mapped_column(Integer, nullable=False)
    votos_legenda: Mapped[int] = mapped_column(Integer, nullable=False)
