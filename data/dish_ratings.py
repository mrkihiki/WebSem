import datetime
import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin

from .db_session import SqlAlchemyBase


class DishRating(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'dish_ratings'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    user_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("users.id"))
    dish_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("dishes.id"))
    rating = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

    # Связи
    user = orm.relationship('User', back_populates='ratings')
    dish = orm.relationship('Dish', back_populates='ratings')

    def __repr__(self):
        return f"<DishRating> user:{self.user_id} dish:{self.dish_id} rating:{self.rating}"
