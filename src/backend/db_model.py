import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, ForeignKey, Integer, Float, String, Unicode, PrimaryKeyConstraint, Date, Time, Boolean, DateTime
from sqlalchemy import types
from sqlalchemy.dialects.mysql.base import MSBinary
import uuid
from sqlalchemy.orm import relationship
from passlib.hash import bcrypt

Base = declarative_base()
ACCESS_FILE_PATH = os.path.dirname(os.path.abspath(__file__)) + '/access.txt'

class UUID(types.TypeDecorator):
    impl = MSBinary
    def __init__(self):
        self.impl.length = 16
        types.TypeDecorator.__init__(self,length=self.impl.length)

    def process_bind_param(self,value,dialect=None):
        if value and isinstance(value,uuid.UUID):
            return value.bytes
        elif value and not isinstance(value,uuid.UUID):
            raise 'value %s is not a valid uuid.UUID' % value
        else:
            return None

    def process_result_value(self,value,dialect=None):
        if value:
            return uuid.UUID(bytes=value)
        else:
            return None

    def is_mutable(self):
        return False

class User(Base):
    __tablename__ = 'user'
    id = Column(Integer, primary_key=True, autoincrement=True)
    face_id = Column(String(256), unique=True, nullable=False)
    password = Column(String(256), nullable=False)
    level = Column(Integer, nullable=False)
    fullname = Column(Unicode(256), nullable=False)
    date_created = Column(DateTime)
    avatar = Column(Unicode(256))
    def __init__(self, face_id, password, date_created, level = 1, fullname=None, avatar=None, ):
        self.face_id = face_id
        self.password = bcrypt.encrypt(password)
        self.level = level
        self.fullname = fullname
        self.avatar = avatar
        self.date_created = date_created

    def validate_password(self, password):
        return bcrypt.verify(password, self.password)

class Schedule(Base):
    __tablename__ = 'schedule'
    #uuid = Column('UUID', UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(Integer, ForeignKey('user.id'))
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    url_image = Column(Unicode(256), nullable=True)

    modify = Column(String(10000))
    user = relationship(User)
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'date'),
        {},
    )

    def __init__(self, user_id, date, start, end, url_image, modify):
        self.user_id = user_id
        self.date = date
        self.start_time = start
        self.end_time = end
        self.modify = modify
        self.url_image = url_image

class AdminSchedule(Base):
    __tablename__ = 'adminschedule'
    user_id = Column(Integer, ForeignKey('user.id'))
    date = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)
    url_image = Column(Unicode(256), nullable=True)
    in_late = Column(Float, nullable=True)
    out_early = Column(String(10), nullable=True)
    ot = Column(Integer)

    user = relationship(User)
    __table_args__ = (
        PrimaryKeyConstraint('user_id', 'date'),
        {},
    )

    def __init__(self, user_id, date, start, end, url_image, in_late, out_early, ot):
        self.user_id = user_id
        self.date = date
        self.start_time = start
        self.end_time = end
        self.url_image = url_image
        self.in_late = in_late
        self.out_early = out_early
        self.ot = ot

class FormTime(Base):
    __tablename__ = 'formtime'
    id = Column(Integer, primary_key=True, autoincrement=True)
    start = Column(Time)
    end = Column(Time)
    money = Column(Float)

    def __init__(self, start, end, money):
        self.start = start
        self.end = end
        self.money = money

class TokenBlacklist(Base):
    __tablename__ = 'tokenblacklist'
    id = Column(Integer, primary_key=True)
    jti = Column(String(36), nullable=False)
    token_type = Column(String(10), nullable=False)
    user_identity = Column(String(50), nullable=False)
    revoked = Column(Boolean, nullable=False)
    expires = Column(DateTime, nullable=False)

    def to_dict(self):
        return {
            'token_id': self.id,
            'jti': self.jti,
            'token_type': self.token_type,
            'user_identity': self.user_identity,
            'revoked': self.revoked,
            'expires': self.expires
        }

class OT(Base):
    __tablename__ = 'register_ot'
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey('user.id'))
    date_created = Column(DateTime)
    date_ot = Column(Date)
    start_time = Column(Time)
    end_time = Column(Time)

    user = relationship(User)
    def __init__(self, user_id, date_created, date_ot, start_time, end_time):
        self.user_id = user_id
        self.date_created = date_created
        self.date_ot = date_ot
        self.start_time = start_time
        self.end_time = end_time

def read_file_config():
    result = {}
    f = open(ACCESS_FILE_PATH, 'r')
    for line in f:
        temp = line.split(':')
        result[temp[0].strip()] = temp[1].strip()
    f.close()
    return result

CONFIG_DIC = read_file_config()

def get_engine():
    user_name = CONFIG_DIC['user']
    password = CONFIG_DIC['password']
    host = CONFIG_DIC['host']
    db_name = CONFIG_DIC['database']
    #mysql_engine_str = 'mysql+mysqldb://%s:%s@%s/%s?charset=utf8mb4' % (user_name, password, host, db_name)
    mysql_engine_str = 'mysql+mysqldb://%s:%s@%s/%s?charset=utf8' % (user_name, password, host, db_name)
    engine = create_engine(mysql_engine_str, pool_recycle=3600 * 7)
    return engine

def create_database():
    engine = get_engine()
    Base.metadata.create_all(engine)

if __name__ == '__main__':
    create_database()

