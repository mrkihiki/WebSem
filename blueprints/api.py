from flask import Blueprint, jsonify, request, abort
from flask_login import login_required, current_user
import json

from data import db_session
from data.dishes import Dish, DishWithRating
from data.dish_ratings import DishRating
from data.favourites import Favourite
from data.users import User

api_bp = Blueprint('api', __name__)


def can_edit_dish(dish, user):
    """Проверяет, может ли пользователь редактировать/удалять блюдо"""
    if not user.is_authenticated:
        return False

    # Админ (ID=1) может всё
    if user.id == 1:
        return True

    # Автор блюда может редактировать свое блюдо
    if dish.author_id == user.id:
        return True

    return False


def is_youtube_link(url):
    return "youtube.com" in url or "youtu.be" in url


def create_json_response(data, status=200):
    from flask import make_response
    response = make_response(json.dumps(data, ensure_ascii=False, indent=2))
    response.headers['Content-Type'] = 'application/json; charset=utf-8'
    response.status_code = status
    return response


def dish_to_dict(dish, include_details=False, session=None):
    close_session = False
    if session is None:
        session = db_session.create_session()
        close_session = True
    data = {
        'id': dish.id,
        'name': dish.name,
        'average_rating': dish.get_average_rating(session),
        'rating_count': dish.get_rating_count(session),
        'is_favourite': dish.is_favourite(current_user.id, session) if current_user.is_authenticated else False,
        # 'author_id': dish.author_id
    }
    # Получаем информацию об авторе
    # if dish.author_id:
    #     author = session.query(User).get(dish.author_id)
    #     if author:
    #         data['author'] = {
    #             'id': author.id,
    #             'login': author.login,
    #             'is_current_user': current_user.is_authenticated and author.id == current_user.id
    #         }
    if include_details:
        data.update({
            'ingredients': dish.ingredients,
            'url': dish.url,
            'user_rating': None
        })

        if current_user.is_authenticated:
            user_rating = session.query(DishRating).filter(
                DishRating.user_id == current_user.id,
                DishRating.dish_id == dish.id
            ).first()
            data['user_rating'] = user_rating.rating if user_rating else None

    if close_session:
        session.close()

    return data


# Блюда
@api_bp.route('/dishes', methods=['GET'])
def get_dishes():
    sort_by = request.args.get('sort', 'default')
    session = db_session.create_session()

    if sort_by == 'rating':
        dishes_query = session.query(DishWithRating).order_by(
            DishWithRating.average_rating.desc()
        ).all()
    else:
        dishes_query = session.query(DishWithRating).all()

    dishes_list = []
    for dish_view in dishes_query:
        dish_data = {
            'id': dish_view.id,
            'name': dish_view.name,
            'average_rating': dish_view.average_rating,
            'rating_count': dish_view.rating_count
        }

        if current_user.is_authenticated:
            favourite = session.query(Favourite).filter(
                Favourite.user_id == current_user.id,
                Favourite.dishes_id == dish_view.id
            ).first()
            dish_data['is_favourite'] = favourite is not None

        dishes_list.append(dish_data)

    session.close()
    return create_json_response({
        'dishes': dishes_list,
        'count': len(dishes_list)
    })


@api_bp.route('/dishes/<int:dish_id>', methods=['GET'])
def get_dish(dish_id):
    session = db_session.create_session()
    dish = session.query(Dish).get(dish_id)
    if not dish:
        session.close()
        return create_json_response({'error': 'Dish not found'}, 404)

    dish_data = dish_to_dict(dish, include_details=True, session=session)
    session.close()
    return create_json_response({'dish': dish_data})


@api_bp.route('/dishes', methods=['POST'])
@login_required
def create_dish():
    if not request.json:
        return create_json_response({'error': 'Empty request'}, 400)

    required_fields = ['name', 'ingredients']
    if not all(field in request.json for field in required_fields):
        return create_json_response({'error': 'Missing required fields'}, 400)

    session = db_session.create_session()

    # Проверка уникальности названия
    existing_dish = session.query(Dish).filter(
        Dish.name == request.json['name']
    ).first()

    if existing_dish:
        session.close()
        return create_json_response({'error': 'Dish with this name already exists'}, 400)
    dish = Dish(
        name=request.json['name'],
        ingredients=request.json['ingredients'],
        url=request.json.get('url')
    )
    if not is_youtube_link(dish.url) and dish.url != "":
        return create_json_response({'error': 'The link should lead to YouTube'}, 400)

    session.add(dish)
    session.commit()
    dish_id = dish.id
    session.close()

    return get_dish(dish_id)


@api_bp.route('/dishes/<int:dish_id>', methods=['PUT'])
@login_required
def update_dish(dish_id):
    if not request.json:
        return create_json_response({'error': 'Empty request'}, 400)
    session = db_session.create_session()
    dish = session.query(Dish).get(dish_id)
    if not dish:
        session.close()
        return create_json_response({'error': 'Dish not found'}, 404)
    # Проверяем права
    if not can_edit_dish(dish, current_user):
        session.close()
        return create_json_response({'error': 'Permission denied'}, 403)
    url = request.json.get("url", "")
    if not is_youtube_link(url) and url != "":
        return create_json_response({'error': 'The link should lead to YouTube'}, 400)
    if dish.name != request.json["name"]:
        existing_dish = session.query(Dish).filter(
            Dish.name == request.json["name"],
            Dish.id != dish.name
        ).first()
        if existing_dish:
            return create_json_response({'error': 'Dish with this name already exists'}, 400)
    # Обновляем поля
    fields = ['name', 'ingredients', 'url']
    for field in fields:
        if field in request.json:
            setattr(dish, field, request.json[field])
    session.commit()
    session.close()
    return get_dish(dish_id)


@api_bp.route('/dishes/<int:dish_id>', methods=['DELETE'])
@login_required
def delete_dish(dish_id):
    session = db_session.create_session()
    dish = session.query(Dish).get(dish_id)

    if not dish:
        session.close()
        return create_json_response({'error': 'Dish not found'}, 404)

    # Проверяем права
    if not can_edit_dish(dish, current_user):
        session.close()
        return create_json_response({'error': 'Permission denied'}, 403)

    session.delete(dish)
    session.commit()
    session.close()

    return create_json_response({'success': 'Dish deleted'})


# Рейтинги
@api_bp.route('/dishes/<int:dish_id>/rate', methods=['POST'])
@login_required
def rate_dish_api(dish_id):
    if not request.json or 'rating' not in request.json:
        return create_json_response({'error': 'Rating required'}, 400)

    rating = request.json['rating']
    if not isinstance(rating, int) or rating < 1 or rating > 5:
        return create_json_response({'error': 'Rating must be integer between 1 and 5'}, 400)

    session = db_session.create_session()

    dish_rating = session.query(DishRating).filter(
        DishRating.user_id == current_user.id,
        DishRating.dish_id == dish_id
    ).first()

    if dish_rating:
        dish_rating.rating = rating
    else:
        dish_rating = DishRating(
            user_id=current_user.id,
            dish_id=dish_id,
            rating=rating
        )
        session.add(dish_rating)

    session.commit()
    session.close()

    return create_json_response({'message': 'Rating saved', 'rating': rating})


@api_bp.route('/dishes/<int:dish_id>/rating', methods=['GET'])
@login_required
def get_user_rating(dish_id):
    session = db_session.create_session()

    dish_rating = session.query(DishRating).filter(
        DishRating.user_id == current_user.id,
        DishRating.dish_id == dish_id
    ).first()

    session.close()

    return create_json_response({
        'rating': dish_rating.rating if dish_rating else None
    })


# Избранное
@api_bp.route('/dishes/<int:dish_id>/favourite', methods=['POST'])
@login_required
def toggle_favourite_api(dish_id):
    session = db_session.create_session()

    favourite = session.query(Favourite).filter(
        Favourite.user_id == current_user.id,
        Favourite.dishes_id == dish_id
    ).first()

    if favourite:
        session.delete(favourite)
        action = 'removed'
    else:
        favourite = Favourite(
            user_id=current_user.id,
            dishes_id=dish_id
        )
        session.add(favourite)
        action = 'added'

    session.commit()
    session.close()

    return create_json_response({
        'message': f'Dish {action} from favourites',
        'is_favourite': action == 'added'
    })


@api_bp.route('/user/favourites', methods=['GET'])
@login_required
def get_user_favourites():
    session = db_session.create_session()

    favourites = session.query(Favourite).filter(
        Favourite.user_id == current_user.id
    ).all()

    dishes = []
    for fav in favourites:
        dish = session.query(Dish).get(fav.dishes_id)
        if dish:
            dishes.append(dish_to_dict(dish, session=session))

    session.close()

    return create_json_response({
        'favourites': dishes,
        'count': len(dishes)
    })
