from contextlib import contextmanager
from datetime import datetime
import os
from pathlib import Path
from typing import List, Optional

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, Integer, JSON, String, Text
from sqlalchemy.orm import sessionmaker, Session, validates
from sqlalchemy.engine import Engine, create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql.expression import desc

from jupyter_cache.utils import shorten_path


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
    """A settings key/value pair representation."""

    __tablename__ = "settings"

    pk = Column(Integer(), primary_key=True)
    key = Column(String(36), nullable=False, unique=True)
    value = Column(JSON())

    def __repr__(self):
        return "{0}(pk={1},{2}={3})".format(
            self.__class__.__name__, self.pk, self.key, self.value
        )

    @staticmethod
    def set_value(key: str, value, db: Engine):
        with session_context(db) as session:  # type: Session
            setting = session.query(Setting).filter_by(key=key).one_or_none()
            if setting is None:
                session.add(Setting(key=key, value=value))
            else:
                setting.value = value
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
                    raise KeyError("Setting not found in DB: {}".format(key))
            value = result[0]
        return value

    @staticmethod
    def get_dict(db: Engine) -> dict:
        with session_context(db) as session:  # type: Session
            results = session.query(Setting.key, Setting.value).all()
        return {k: v for k, v in results}


class NbCacheRecord(OrmBase):
    """A record of an executed notebook cache."""

    __tablename__ = "nbcache"

    pk = Column(Integer(), primary_key=True)
    hashkey = Column(String(255), nullable=False, unique=True)
    uri = Column(String(255), nullable=False, unique=False)
    description = Column(String(255), nullable=False, default="")
    data = Column(JSON())
    created = Column(DateTime, nullable=False, default=datetime.utcnow)
    accessed = Column(
        DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow
    )

    def __repr__(self):
        return "{0}(pk={1})".format(self.__class__.__name__, self.pk)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def format_dict(
        self, hashkey=False, path_length=None, show_descript=False, show_data=True
    ):
        data = {
            "ID": self.pk,
            "Origin URI": str(shorten_path(self.uri, path_length)),
            "Created": self.created.isoformat(" ", "minutes"),
            "Accessed": self.accessed.isoformat(" ", "minutes"),
        }
        if show_descript:
            data["Description"] = self.description
        if hashkey:
            data["Hashkey"] = self.hashkey
        if show_data and self.data:
            data["Data"] = self.data
        return data

    @staticmethod
    def create_record(uri: str, hashkey: str, db: Engine, **kwargs) -> "NbCacheRecord":
        with session_context(db) as session:  # type: Session
            record = NbCacheRecord(hashkey=hashkey, uri=uri, **kwargs)
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
            session.query(NbCacheRecord).filter(NbCacheRecord.pk.in_(pks)).delete(
                synchronize_session=False
            )
            session.commit()

    @staticmethod
    def record_from_hashkey(hashkey: str, db: Engine) -> "NbCacheRecord":
        with session_context(db) as session:  # type: Session
            result = (
                session.query(NbCacheRecord).filter_by(hashkey=hashkey).one_or_none()
            )
            if result is None:
                raise KeyError(
                    "Cache record not found for NB with hashkey: {}".format(hashkey)
                )
            session.expunge(result)
        return result

    @staticmethod
    def record_from_pk(pk: int, db: Engine) -> "NbCacheRecord":
        with session_context(db) as session:  # type: Session
            result = session.query(NbCacheRecord).filter_by(pk=pk).one_or_none()
            if result is None:
                raise KeyError("Cache record not found for NB with PK: {}".format(pk))
            session.expunge(result)
        return result

    def touch(pk, db: Engine):
        """Touch a record, to change its last accessed time."""
        with session_context(db) as session:  # type: Session
            record = session.query(NbCacheRecord).filter_by(pk=pk).one_or_none()
            if record is None:
                raise KeyError("Cache record not found for NB with PK: {}".format(pk))
            record.accessed = datetime.utcnow()
            session.commit()

    def touch_hashkey(hashkey, db: Engine):
        """Touch a record, to change its last accessed time."""
        with session_context(db) as session:  # type: Session
            record = (
                session.query(NbCacheRecord).filter_by(hashkey=hashkey).one_or_none()
            )
            if record is None:
                raise KeyError(
                    "Cache record not found for NB with hashkey: {}".format(hashkey)
                )
            record.accessed = datetime.utcnow()
            session.commit()

    @staticmethod
    def records_from_uri(uri: str, db: Engine) -> "NbCacheRecord":
        with session_context(db) as session:  # type: Session
            results = session.query(NbCacheRecord).filter_by(uri=uri).all()
            session.expunge_all()
        return results

    @staticmethod
    def records_all(db: Engine) -> "NbCacheRecord":
        with session_context(db) as session:  # type: Session
            results = session.query(NbCacheRecord).all()
            session.expunge_all()
        return results

    def records_to_delete(keep: int, db: Engine) -> List[int]:
        """Return pks of the oldest records, where keep is number to keep."""
        with session_context(db) as session:  # type: Session
            pks_to_keep = [
                pk
                for pk, in session.query(NbCacheRecord.pk)
                .order_by(desc("accessed"))
                .limit(keep)
                .all()
            ]
            pks_to_delete = [
                pk
                for pk, in session.query(NbCacheRecord.pk)
                .filter(NbCacheRecord.pk.notin_(pks_to_keep))
                .all()
            ]
        return pks_to_delete


class NbStageRecord(OrmBase):
    """A record of a notebook staged for execution."""

    __tablename__ = "nbstage"

    pk = Column(Integer(), primary_key=True)
    uri = Column(String(255), nullable=False, unique=True)
    assets = Column(JSON(), nullable=False, default=list)
    traceback = Column(Text(), nullable=True, default="")
    created = Column(DateTime, nullable=False, default=datetime.utcnow)

    def __repr__(self):
        return "{0}(pk={1})".format(self.__class__.__name__, self.pk)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}

    def format_dict(self, cache_record=None, path_length=None, assets=True):
        data = {
            "ID": self.pk,
            "URI": str(shorten_path(self.uri, path_length)),
            "Created": self.created.isoformat(" ", "minutes"),
        }
        if assets:
            data["Assets"] = len(self.assets)
        if cache_record is not None:
            data["Cache ID"] = cache_record.pk
        return data

    @validates("assets")
    def validator_assets(self, key, value):
        return self.validate_assets(value)

    @staticmethod
    def validate_assets(paths, uri=None):
        """Validate asset paths are within same folder as the notebook URI"""
        if not (
            isinstance(paths, (list, tuple)) and all(isinstance(v, str) for v in paths)
        ):
            raise TypeError(f"assets must be interable of strings: {paths}")
        if uri is None:
            return list(paths)

        uri_folder = Path(uri).parent
        for path in paths:
            try:
                Path(path).relative_to(uri_folder)
            except ValueError:
                raise ValueError(f"Asset '{path}' is not in folder '{uri_folder}''")
        return list(paths)

    @staticmethod
    def create_record(
        uri: str, db: Engine, raise_on_exists=True, assets=()
    ) -> "NbStageRecord":
        assets = NbStageRecord.validate_assets(assets, uri)
        with session_context(db) as session:  # type: Session
            record = NbStageRecord(uri=uri, assets=assets)
            session.add(record)
            try:
                session.commit()
            except IntegrityError:
                if raise_on_exists:
                    raise ValueError(f"uri already staged: {uri}")
                return NbStageRecord.record_from_uri(uri, db)
            session.refresh(record)
            session.expunge(record)
        return record

    def remove_pks(pks: List[int], db: Engine):
        with session_context(db) as session:  # type: Session
            session.query(NbStageRecord).filter(NbStageRecord.pk.in_(pks)).delete(
                synchronize_session=False
            )
            session.commit()

    def remove_uris(uris: List[str], db: Engine):
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
                raise KeyError("Staging record not found for NB with PK: {}".format(pk))
            session.expunge(result)
        return result

    @staticmethod
    def record_from_uri(uri: str, db: Engine) -> "NbStageRecord":
        with session_context(db) as session:  # type: Session
            result = session.query(NbStageRecord).filter_by(uri=uri).one_or_none()
            if result is None:
                raise KeyError(
                    "Staging record not found for NB with URI: {}".format(uri)
                )
            session.expunge(result)
        return result

    @staticmethod
    def records_all(db: Engine) -> "NbStageRecord":
        with session_context(db) as session:  # type: Session
            results = session.query(NbStageRecord).all()
            session.expunge_all()
        return results

    def remove_tracebacks(pks, db: Engine):
        """Remove all tracebacks."""
        with session_context(db) as session:  # type: Session
            session.query(NbStageRecord).filter(NbStageRecord.pk.in_(pks)).update(
                {NbStageRecord.traceback: None}, synchronize_session=False
            )
            session.commit()

    def set_traceback(uri: str, traceback: Optional[str], db: Engine):
        with session_context(db) as session:  # type: Session
            result = session.query(NbStageRecord).filter_by(uri=uri).one_or_none()
            if result is None:
                raise KeyError(
                    "Staging record not found for NB with URI: {}".format(uri)
                )
            result.traceback = traceback
            try:
                session.commit()
            except IntegrityError:
                raise TypeError(traceback)
