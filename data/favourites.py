import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class Favourite(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'favourites'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("users.id"))
    dishes_id = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey("dishes.id"))

    # Связи
    user = orm.relationship('User', back_populates='favourites')
    dish = orm.relationship('Dish', back_populates='favourites')

    def __repr__(self):
        return f"<Favourite> user:{self.user_id} dish:{self.dishes_id}"
