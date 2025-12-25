import sqlalchemy
from sqlalchemy import orm
from sqlalchemy_serializer import SerializerMixin
from sqlalchemy import func
from .db_session import SqlAlchemyBase


class Dish(SqlAlchemyBase, SerializerMixin):
    __tablename__ = 'dishes'

    id = sqlalchemy.Column(sqlalchemy.Integer,
                           primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True, unique=True)
    ingredients = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    url = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    author_id = sqlalchemy.Column(sqlalchemy.Integer,
                                  sqlalchemy.ForeignKey("users.id"),
                                  nullable=True)

    # Связи
    ratings = orm.relationship("DishRating", back_populates='dish')
    favourites = orm.relationship("Favourite", back_populates='dish')
    author = orm.relationship('User', backref='created_dishes')

    def get_average_rating(self, session=None):
        from .dish_ratings import DishRating
        if session is None:
            from .db_session import create_session
            session = create_session()

        result = session.query(func.avg(DishRating.rating)).filter(
            DishRating.dish_id == self.id
        ).scalar()

        session.close()
        return round(result, 2) if result else 0

    def get_rating_count(self, session=None):
        from .dish_ratings import DishRating
        if session is None:
            from .db_session import create_session
            session = create_session()

        result = session.query(func.count(DishRating.rating)).filter(
            DishRating.dish_id == self.id
        ).scalar()

        session.close()
        return result or 0

    def is_favourite(self, user_id, session=None):
        from .favourites import Favourite
        if session is None:
            from .db_session import create_session
            session = create_session()
        result = session.query(Favourite).filter(
            Favourite.user_id == user_id,
            Favourite.dishes_id == self.id
        ).first() is not None

        session.close()
        return result

    def __repr__(self):
        return f"<Dish> {self.name} {self.ingredients}"


# Модель для представления dishes_with_ratings
class DishWithRating(SqlAlchemyBase):
    __tablename__ = 'dishes_with_ratings'
    __table_args__ = {'info': {'is_view': True}}

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True)
    name = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    ingredients = sqlalchemy.Column(sqlalchemy.Text, nullable=True)
    url = sqlalchemy.Column(sqlalchemy.String, nullable=True)
    average_rating = sqlalchemy.Column(sqlalchemy.Float, nullable=True)
    rating_count = sqlalchemy.Column(sqlalchemy.Integer, nullable=True)

    def __repr__(self):
        return f"<DishWithRating> {self.id} {self.name} - {self.average_rating}"
