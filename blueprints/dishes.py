from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from data import db_session
from data.dishes import Dish, DishWithRating
from data.dish_ratings import DishRating
from data.favourites import Favourite
from forms.dish import AddDishForm

dishes_bp = Blueprint('dishes', __name__)


@dishes_bp.route('/dishes', methods=['GET'])
@login_required
def dishes_list():
    sort_by = request.args.get('sort', 'default')

    session = db_session.create_session()

    if sort_by == 'rating':
        # Используем view для сортировки по рейтингу
        dishes_query = session.query(DishWithRating).order_by(
            desc(DishWithRating.average_rating)
        ).all()
    elif sort_by == 'favourites':
        # Показываем только избранные
        favourites = session.query(Favourite).filter(
            Favourite.user_id == current_user.id
        ).all()
        dish_ids = [fav.dishes_id for fav in favourites]
        dishes_query = session.query(DishWithRating).filter(
            DishWithRating.id.in_(dish_ids)
        ).all()
    else:
        dishes_query = session.query(DishWithRating).all()

    # Получаем дополнительную информацию для каждого блюда
    dishes = []
    for dish_view in dishes_query:
        dish_info = {
            'id': dish_view.id,
            'name': dish_view.name,
            'ingredients': dish_view.ingredients,
            'url': dish_view.url,
            'average_rating': dish_view.average_rating,
            'rating_count': dish_view.rating_count,
            'is_favourite': False,
            'user_rating': None
        }

        # Проверяем, в избранном ли
        favourite = session.query(Favourite).filter(
            Favourite.user_id == current_user.id,
            Favourite.dishes_id == dish_view.id
        ).first()
        dish_info['is_favourite'] = favourite is not None

        # Получаем оценку пользователя
        user_rating = session.query(DishRating).filter(
            DishRating.user_id == current_user.id,
            DishRating.dish_id == dish_view.id
        ).first()
        dish_info['user_rating'] = user_rating.rating if user_rating else None

        dishes.append(dish_info)

    session.close()

    return render_template('dishes.html',
                           title='Список блюд',
                           dishes=dishes,
                           current_sort=sort_by,
                           get_navbar=get_navbar(),
                           get_footer=get_footer())


@dishes_bp.route('/dishes/<int:dish_id>', methods=['GET'])
@login_required
def dish_detail(dish_id):
    session = db_session.create_session()

    dish = session.query(Dish).get(dish_id)
    if not dish:
        flash('Блюдо не найдено', 'danger')
        session.close()
        return redirect(url_for('dishes.dishes_list'))

    # Получаем информацию из view
    dish_view = session.query(DishWithRating).get(dish_id)

    # Получаем оценку пользователя
    user_rating = session.query(DishRating).filter(
        DishRating.user_id == current_user.id,
        DishRating.dish_id == dish_id
    ).first()

    # Проверяем, в избранном ли
    favourite = session.query(Favourite).filter(
        Favourite.user_id == current_user.id,
        Favourite.dishes_id == dish_id
    ).first()

    session.close()

    return render_template('dish_detail.html',
                           title=dish.name,
                           dish=dish,
                           dish_view=dish_view,
                           user_rating=user_rating.rating if user_rating else None,
                           is_favourite=favourite is not None,
                           get_navbar=get_navbar(),
                           get_footer=get_footer())


@dishes_bp.route('/dishes/add', methods=['GET', 'POST'])
@login_required
def add_dish():
    form = AddDishForm()

    if form.validate_on_submit():
        session = db_session.create_session()

        # Проверяем, есть ли уже такое блюдо
        existing_dish = session.query(Dish).filter(
            Dish.name == form.name.data
        ).first()

        if existing_dish:
            flash('Блюдо с таким названием уже существует', 'danger')
            session.close()
            return redirect(url_for('dishes.add_dish'))

        dish = Dish(
            name=form.name.data,
            ingredients=form.ingredients.data,
            url=form.url.data if form.url.data else None
        )

        session.add(dish)
        session.commit()
        session.close()

        flash(f'Блюдо "{dish.name}" успешно добавлено!', 'success')
        return redirect(url_for('dishes.dishes_list'))

    return render_template('add_dish.html',
                           title='Добавить блюдо',
                           form=form,
                           get_navbar=get_navbar(),
                           get_footer=get_footer())


@dishes_bp.route('/dishes/<int:dish_id>/rate', methods=['POST'])
@login_required
def rate_dish(dish_id):
    rating = request.form.get('rating', type=int)

    if not rating or rating < 1 or rating > 5:
        flash('Рейтинг должен быть от 1 до 5', 'danger')
        return redirect(url_for('dishes.dish_detail', dish_id=dish_id))

    session = db_session.create_session()

    # Проверяем, есть ли уже оценка
    dish_rating = session.query(DishRating).filter(
        DishRating.user_id == current_user.id,
        DishRating.dish_id == dish_id
    ).first()

    if dish_rating:
        dish_rating.rating = rating
        flash('Рейтинг обновлен', 'success')
    else:
        dish_rating = DishRating(
            user_id=current_user.id,
            dish_id=dish_id,
            rating=rating
        )
        session.add(dish_rating)
        flash('Рейтинг добавлен', 'success')

    session.commit()
    session.close()

    return redirect(url_for('dishes.dish_detail', dish_id=dish_id))


@dishes_bp.route('/dishes/<int:dish_id>/toggle_favourite', methods=['POST'])
@login_required
def toggle_favourite(dish_id):
    session = db_session.create_session()

    favourite = session.query(Favourite).filter(
        Favourite.user_id == current_user.id,
        Favourite.dishes_id == dish_id
    ).first()

    if favourite:
        session.delete(favourite)
        flash('Удалено из избранного', 'info')
    else:
        favourite = Favourite(
            user_id=current_user.id,
            dishes_id=dish_id
        )
        session.add(favourite)
        flash('Добавлено в избранное', 'success')

    session.commit()
    session.close()

    return redirect(url_for('dishes.dish_detail', dish_id=dish_id))


# Вспомогательные функции для шаблонов
def get_navbar():
    from app import get_navbar as app_get_navbar
    return app_get_navbar()


def get_footer():
    from app import get_footer as app_get_footer
    return app_get_footer()