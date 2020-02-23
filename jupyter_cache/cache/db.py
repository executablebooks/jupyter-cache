from contextlib import contextmanager
from datetime import datetime
import os
from typing import List

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, JSON, String
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import desc


OrmBase = declarative_base()


def create_db(path, name="global.db") -> Engine:
    engine = create_engine("sqlite:///{}".format(os.path.join(path, name)))
    OrmBase.metadata.create_all(engine)
    return engine


@contextmanager
def session_context(engine: Engine):
    """Open a connection to the database."""
    session = sessionmaker(bind=engine)()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


class Setting(OrmBase):
    __tablename__ = "settings"

    pk = Column(Integer(), primary_key=True)
    key = Column(String(36), nullable=False, unique=True)
    value = Column(JSON())

    @staticmethod
    def set_value(key: str, value, db: Engine):
        with session_context(db) as session:  # type: Session
            setting = session.query(Setting).filter_by(key=key).one_or_none()
            if setting is None:
                session.add(Setting(key=key, value=value))
            else:
                setting.value = value
                session.merge(setting)
            try:
                session.commit()
            except IntegrityError:
                raise TypeError(value)

    @staticmethod
    def get_value(key: str, db: Engine, default=None):
        with session_context(db) as session:  # type: Session
            result = session.query(Setting.value).filter_by(key=key).one_or_none()
            if result is None:
                if default is not None:
                    Setting.set_value(key, default, db)
                    result = [default]
                else:
                    raise KeyError(key)
            value = result[0]
        return value

    @staticmethod
    def get_dict(db: Engine) -> dict:
        with session_context(db) as session:  # type: Session
            results = session.query(Setting.key, Setting.value).all()
        return {k: v for k, v in results}


class NbCommitRecord(OrmBase):
    __tablename__ = "nbcommit"

    pk = Column(Integer(), primary_key=True)
    hashkey = Column(String(255), nullable=False, unique=True)
    uri = Column(String(255), nullable=False, unique=False)
    description = Column(String(255), nullable=False, default="")
    data = Column(JSON())
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    accessed = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @staticmethod
    def create_record(uri: str, hashkey: str, db: Engine, **kwargs) -> "NbCommitRecord":
        with session_context(db) as session:  # type: Session
            record = NbCommitRecord(hashkey=hashkey, uri=uri, **kwargs)
            session.add(record)
            try:
                session.commit()
            except IntegrityError:
                raise ValueError(f"hashkey already exists:{hashkey}")
            session.refresh(record)
            session.expunge(record)
        return record

    def remove_records(pks: List[int], db: Engine):
        with session_context(db) as session:  # type: Session
            session.query(NbCommitRecord).filter(NbCommitRecord.pk.in_(pks)).delete(
                synchronize_session=False
            )
            session.commit()

    @staticmethod
    def record_from_hashkey(hashkey: str, db: Engine) -> "NbCommitRecord":
        with session_context(db) as session:  # type: Session
            result = (
                session.query(NbCommitRecord).filter_by(hashkey=hashkey).one_or_none()
            )
            if result is None:
                raise KeyError(hashkey)
            session.expunge(result)
        return result

    @staticmethod
    def record_from_pk(pk: int, db: Engine) -> "NbCommitRecord":
        with session_context(db) as session:  # type: Session
            result = session.query(NbCommitRecord).filter_by(pk=pk).one_or_none()
            if result is None:
                raise KeyError(pk)
            session.expunge(result)
        return result

    def touch(pk, db: Engine):
        """Touch a record, to change its last accessed time."""
        with session_context(db) as session:  # type: Session
            record = session.query(NbCommitRecord).filter_by(pk=pk).one_or_none()
            if record is None:
                raise KeyError(pk)
            record.accessed = datetime.utcnow()
            session.merge(record)
            session.commit()

    def touch_hashkey(hashkey, db: Engine):
        """Touch a record, to change its last accessed time."""
        with session_context(db) as session:  # type: Session
            record = (
                session.query(NbCommitRecord).filter_by(hashkey=hashkey).one_or_none()
            )
            if record is None:
                raise KeyError(hashkey)
            record.accessed = datetime.utcnow()
            session.merge(record)
            session.commit()

    @staticmethod
    def records_from_uri(uri: str, db: Engine) -> "NbCommitRecord":
        with session_context(db) as session:  # type: Session
            results = session.query(NbCommitRecord).filter_by(uri=uri).all()
            session.expunge_all()
        return results

    @staticmethod
    def records_all(db: Engine) -> "NbCommitRecord":
        with session_context(db) as session:  # type: Session
            results = session.query(NbCommitRecord).all()
            session.expunge_all()
        return results

    def records_to_delete(keep: int, db: Engine) -> List[int]:
        """Return pks of the oldest records, where keep is number to keep."""
        with session_context(db) as session:  # type: Session
            pks_to_keep = [
                pk
                for pk, in session.query(NbCommitRecord.pk)
                .order_by(desc("accessed"))
                .limit(keep)
                .all()
            ]
            pks_to_delete = [
                pk
                for pk, in session.query(NbCommitRecord.pk)
                .filter(NbCommitRecord.pk.notin_(pks_to_keep))
                .all()
            ]
        return pks_to_delete


class NbStageRecord(OrmBase):
    __tablename__ = "nbstage"

    pk = Column(Integer(), primary_key=True)
    uri = Column(String(255), nullable=False, unique=True)
    created = Column(DateTime, nullable=False, default=datetime.utcnow)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    @staticmethod
    def create_record(uri: str, db: Engine, raise_on_exists=True) -> "NbStageRecord":
        with session_context(db) as session:  # type: Session
            record = NbStageRecord(uri=uri)
            session.add(record)
            try:
                session.commit()
            except IntegrityError:
                if raise_on_exists:
                    raise ValueError(f"uri already staged: {uri}")
            session.refresh(record)
            session.expunge(record)
        return record

    def remove_uris(uris: List[int], db: Engine):
        with session_context(db) as session:  # type: Session
            session.query(NbStageRecord).filter(NbStageRecord.uri.in_(uris)).delete(
                synchronize_session=False
            )
            session.commit()

    @staticmethod
    def record_from_pk(pk: int, db: Engine) -> "NbStageRecord":
        with session_context(db) as session:  # type: Session
            result = session.query(NbStageRecord).filter_by(pk=pk).one_or_none()
            if result is None:
                raise KeyError(pk)
            session.expunge(result)
        return result

    @staticmethod
    def record_from_uri(uri: str, db: Engine) -> "NbStageRecord":
        with session_context(db) as session:  # type: Session
            result = session.query(NbStageRecord).filter_by(uri=uri).one_or_none()
            if result is None:
                raise KeyError(uri)
            session.expunge(result)
        return result

    @staticmethod
    def records_all(db: Engine) -> "NbStageRecord":
        with session_context(db) as session:  # type: Session
            results = session.query(NbStageRecord).all()
            session.expunge_all()
        return results
