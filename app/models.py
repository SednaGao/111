from .db import *
from flask import request, url_for, redirect, render_template, flash, current_app as app
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import func
from flask_security import UserMixin, RoleMixin
from sqlalchemy_serializer import SerializerMixin
import datetime
import enum

#   https://pythonhosted.org/Flask-Security/quickstart.html
#   python manage.py db upgrade && python manage.py db revision --autogenerate


class UserAccountType(enum.Enum):
    MINION = 1
    HUMAN = 2
    CUSTOMER_HUMAN = 2


class BaseModel(db.Model, SerializerMixin):
    __abstract__ = True
    __table_args__ = ({'mysql_engine': 'InnoDB'},)


class BaseEntityModel(BaseModel):
    __abstract__ = True
    id = db.Column(db.Integer,  primary_key=True)
    date_created = db.Column(db.DATETIME, default=func.current_timestamp())
    date_modified = db.Column(db.DATETIME, default=func.current_timestamp(), onupdate=func.current_timestamp())


roles_users = db.Table(
    'roles_users',
    db.Column('final_user_id', db.Integer(), db.ForeignKey('final_user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id')))


class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    description = db.Column(db.String(255))


class FinalUser(BaseEntityModel, UserMixin):
    social_id = db.Column(db.String(64), nullable=True, unique=True)
    email = db.Column(db.String(64), unique=True)
    mobile = db.Column(db.String(32), unique=True, nullable=True)
    password = db.Column(db.String(255))
    last_login_at = db.Column(db.DateTime(), nullable=True)
    last_login_ip = db.Column(db.String(45), nullable=True)
    login_count = db.Column(db.Integer, default=0)
    active = db.Column(db.Boolean(), default=True)
    balance = db.Column(db.Float(), default=0.0)

    roles = db.relationship('Role', secondary=roles_users,
                            backref=db.backref('users', lazy='dynamic'))

    serialize_only = ()
