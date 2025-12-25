from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import sqlalchemy
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import orm
import datetime
from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, UserMixin, SerializerMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    login = sqlalchemy.Column(sqlalchemy.String,
                              index=True, unique=True, nullable=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String, nullable=True)

    # Связи
    ratings = orm.relationship("DishRating", back_populates='user')
    favourites = orm.relationship("Favourite", back_populates='user')

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def __repr__(self):
        return f"<User> {self.id} {self.login}"
