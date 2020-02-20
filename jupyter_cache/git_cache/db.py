from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String

OrmBase = declarative_base()


class OrmNotebook(OrmBase):
    __tablename__ = "notebooks"

    pk = Column(Integer(), primary_key=True)
    uri = Column(String(255), nullable=False, unique=True)
