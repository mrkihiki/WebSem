from flask import Flask, redirect, url_for, render_template, request, jsonify
from flask_bootstrap import Bootstrap5
from flask_login import current_user, LoginManager

from data import db_session
from data.users import User
from data.dishes import Dish
from data.dish_ratings import DishRating
from data.favourites import Favourite
from sqlalchemy import func, desc, text
from blueprints.auth import auth_bp
from blueprints.dishes import dishes_bp
from blueprints.api import api_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'my_secret_key'
bootstrap = Bootstrap5(app)
login_manager = LoginManager()
login_manager.init_app(app)

app.register_blueprint(auth_bp)
app.register_blueprint(dishes_bp)
app.register_blueprint(api_bp, url_prefix='/api')

def get_navbar():
    navbar_html = '''<nav class="navbar navbar-expand-lg navbar-dark bg-dark">
        <div class="container">
            <a class="navbar-brand" href="/">
                <i class="fas fa-utensils"></i> Рецензии на блюда
            </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav me-auto">'''

    if current_user.is_authenticated:
        navbar_html += f'''
                    <li class="nav-item">
                        <a class="nav-link" href="{url_for('dishes.dishes_list')}">
                            <i class="fas fa-list"></i> Все блюда
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{url_for('dishes.dishes_list', sort='favourites')}">
                            <i class="fas fa-star"></i> Избранное
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{url_for('dishes.add_dish')}">
                            <i class="fas fa-plus"></i> Добавить блюдо
                        </a>
                    </li>'''

    navbar_html += '''</ul><ul class="navbar-nav">'''

    if current_user.is_authenticated:
        navbar_html += f'''
                    <li class="nav-item dropdown">
                        <a class="nav-link dropdown-toggle" href="#" id="userDropdown" role="button" 
                           data-bs-toggle="dropdown">
                            <i class="fas fa-user"></i> {current_user.login}
                        </a>
                        <ul class="dropdown-menu">
                            <li><a class="dropdown-item" href="{url_for('auth.logout')}">
                                <i class="fas fa-sign-out-alt"></i> Выйти
                            </a></li>
                        </ul>
                    </li>'''
    else:
        navbar_html += f'''
                    <li class="nav-item">
                        <a class="nav-link" href="{url_for('auth.login')}">
                            <i class="fas fa-sign-in-alt"></i> Войти
                        </a>
                    </li>
                    <li class="nav-item">
                        <a class="nav-link" href="{url_for('auth.register')}">
                            <i class="fas fa-user-plus"></i> Регистрация
                        </a>
                    </li>'''

    navbar_html += '''</ul></div></div></nav>'''
    return navbar_html


def get_footer():
    return '''<footer class="bg-dark text-white py-4 mt-5">
        <div class="container text-center">
            <p>&copy; 2025 Рецензии на блюда.</p>
            <p class="mb-0">
                <a href="/api/dishes" class="text-white">API</a> | 
                <a href="https://github.com" class="text-white">GitHub</a>
            </p>
        </div>
    </footer>'''


@login_manager.user_loader
def load_user(user_id):
    session = db_session.create_session()
    return session.query(User).get(int(user_id))


@login_manager.unauthorized_handler
def unauthorized():
    # Для API возвращаем JSON
    if request.blueprint == 'api':
        return jsonify({'error': 'Authentication required'}), 401
    # Для веб-интерфейса - редирект на страницу входа
    return redirect(url_for('auth.login'))


def seed_database():
    session = db_session.create_session()

    # Создаем тестового пользователя если его нет
    if not session.query(User).filter(User.login == 'admin').first():
        admin = User(login='admin')
        admin.set_password('admin123')
        session.add(admin)

    # Тестовые блюда
    test_dishes = [
        {
            'name': 'Паста Карбонара',
            'ingredients': 'Спагетти, бекон, яйца, сыр пармезан, черный перец, соль',
            'url': 'https://www.youtube.com/embed/D_2DBLAt57c'
        },
        {
            'name': 'Салат Цезарь',
            'ingredients': 'Куриное филе, салат романо, сухарики, сыр пармезан, соус цезарь',
            'url': 'https://www.youtube.com/embed/BqG7tQY3gEI'
        },
        {
            'name': 'Борщ',
            'ingredients': 'Свекла, капуста, картофель, морковь, лук, говядина, сметана',
            'url': 'https://www.youtube.com/embed/ZY8K_cFq-Xc'
        },
        {
            'name': 'Пельмени',
            'ingredients': 'Мука, яйца, вода, говядина, свинина, лук, соль, перец',
            'url': 'https://www.youtube.com/embed/q8VyKXm6R8E'
        },
        {
            'name': 'Пицца Маргарита',
            'ingredients': 'Мука, дрожжи, помидоры, сыр моцарелла, базилик, оливковое масло',
            'url': 'https://www.youtube.com/embed/9f9-xE3tEEk'
        }
    ]

    # Добавляем тестовые блюда
    for dish_data in test_dishes:
        if not session.query(Dish).filter(Dish.name == dish_data['name']).first():
            dish = Dish(**dish_data)
            session.add(dish)

    session.commit()

    # Создаем тестовые оценки и избранное
    admin = session.query(User).filter(User.login == 'admin').first()
    if admin:
        dishes = session.query(Dish).all()

        # Добавляем оценки
        ratings = [
            {'dish': dishes[0], 'rating': 5},
            {'dish': dishes[1], 'rating': 4},
            {'dish': dishes[2], 'rating': 5},
            {'dish': dishes[3], 'rating': 3},
            {'dish': dishes[4], 'rating': 4}
        ]

        for rating_data in ratings:
            existing_rating = session.query(DishRating).filter(
                DishRating.user_id == admin.id,
                DishRating.dish_id == rating_data['dish'].id
            ).first()

            if not existing_rating:
                dish_rating = DishRating(
                    user_id=admin.id,
                    dish_id=rating_data['dish'].id,
                    rating=rating_data['rating']
                )
                session.add(dish_rating)

        # Добавляем в избранное
        favourite_dishes = [dishes[0], dishes[2], dishes[4]]
        for dish in favourite_dishes:
            existing_fav = session.query(Favourite).filter(
                Favourite.user_id == admin.id,
                Favourite.dishes_id == dish.id
            ).first()

            if not existing_fav:
                favourite = Favourite(
                    user_id=admin.id,
                    dishes_id=dish.id
                )
                session.add(favourite)

    session.commit()
    session.close()
    print("База данных успешно заполнена тестовыми данными!")


def create_views():
    """Создает необходимые представления в базе данных"""
    session = db_session.create_session()
    try:
        # Пробуем удалить как таблицу
        session.execute(text("DROP TABLE IF EXISTS dishes_with_ratings"))
        print("Таблица dishes_with_ratings удалена")
    except:
        # Пробуем удалить как представление
        try:
            session.execute(text("DROP VIEW IF EXISTS dishes_with_ratings"))
            print("Представление dishes_with_ratings удалено")
        except:
            pass
    finally:
        session.close()
    try:
        session = db_session.create_session()
        # Создаем представление dishes_with_ratings
        session.execute(text("""
            CREATE VIEW dishes_with_ratings AS
            SELECT 
                d.id,
                d.name,
                d.ingredients,
                d.url,
                COALESCE(AVG(dr.rating), 0) as average_rating,
                COUNT(dr.rating) as rating_count
            FROM dishes d
            LEFT JOIN dish_ratings dr ON d.id = dr.dish_id
            GROUP BY d.id
        """))

        session.commit()
        print("Представление dishes_with_ratings успешно создано")
    except Exception as e:
        print(f"Ошибка при создании представления: {e}")
        session.rollback()
    finally:
        session.close()


@app.route('/')
@app.route('/index')
def index():
    db_sess = db_session.create_session()
    dish_all = db_sess.query(Dish).order_by(Dish.id).all()
    if current_user.is_authenticated:
        return redirect(url_for('dishes.dishes_list'))
    return render_template('index.html',
                           title='Главная',
                           get_navbar=get_navbar(),
                           get_footer=get_footer())


if __name__ == '__main__':
    # Инициализация базы данных
    db_session.global_init("db/my.db")

    # Создаем необходимые представления
    create_views()

    # Заполняем базу тестовыми данными
    seed_database()

    # Запускаем приложение
    app.run(port=8080, host='127.0.0.1')
