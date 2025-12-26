import sys
import os

os.environ["FLASK_ENV"] = "testing"
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import pytest
from app import app
from data import db_session
from data.dishes import Dish
from data.favourites import Favourite
from data.dish_ratings import DishRating
import blueprints.api as api  # blueprint с блюдами


# ---------- ИНИЦИАЛИЗАЦИЯ БД ----------

@pytest.fixture(scope="session", autouse=True)
def setup_db():
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    db_path = os.path.join(BASE_DIR, "tests", "test.db")
    db_session.global_init(db_path)


# ---------- FLASK CLIENT ----------

@pytest.fixture(scope="function")
def client():
    app.config["TESTING"] = True

    if "api" not in app.blueprints:
        app.register_blueprint(api.api_bp, url_prefix="/api")

    with app.test_client() as client:
        yield client


# ---------- ВСПОМОГАТЕЛЬНЫЕ ----------

def login_as_captain(client):
    """Авторизация администратора (id=1)"""
    with client.session_transaction() as sess:
        sess["_user_id"] = "1"


def logout(client):
    with client.session_transaction() as sess:
        sess.clear()


def create_test_dish():
    try:
        dell_test_dish()
    except:
        pass
    session = db_session.create_session()
    dish = Dish(
        name="Test Dish",
        ingredients="Water, Salt",
        url="https://youtube.com/watch?v=test"
    )
    session.add(dish)
    session.commit()
    dish_id = dish.id
    session.close()
    return dish_id


def dell_test_dish():
    session = db_session.create_session()
    session.query(Dish).filter(Dish.name == "Test Dish").delete()
    session.commit()
    session.close()


# =====================================================
# 1. ПОЛУЧЕНИЕ БЛЮД
# =====================================================
# Проверяем: получение списка всех блюд
def test_get_all_dishes(client):
    response = client.get("/api/dishes")
    assert response.status_code == 200
    data = response.get_json()
    assert "dishes" in data
    assert isinstance(data["dishes"], list)


# Проверяем: получение одного блюда по корректному id
def test_get_one_dish_correct(client):
    dish_id = create_test_dish()
    response = client.get(f"/api/dishes/{dish_id}")
    assert response.status_code == 200
    data = response.get_json()
    assert data["dish"]["id"] == dish_id
    dell_test_dish()


# Проверяем: получение блюда по несуществующему id
def test_get_one_dish_not_found(client):
    response = client.get("/api/dishes/999999")
    assert response.status_code == 404


# =====================================================
# 2. СОЗДАНИЕ БЛЮДА
# =====================================================
# Проверяем: корректное создание блюда авторизованным пользователем
def test_create_dish_correct(client):
    login_as_captain(client)

    payload = {
        "name": "New Dish",
        "ingredients": "Cheese, Bread",
        "url": "https://youtu.be/test"
    }
    response = client.post("/api/dishes", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["dish"]["name"] == "New Dish"

    # очистка
    session = db_session.create_session()
    dish = session.query(Dish).filter(Dish.name == "New Dish").first()
    session.delete(dish)
    session.commit()
    session.close()

    logout(client)


# Проверяем: ошибка при создании блюда без обязательных полей
def test_create_dish_missing_fields(client):
    login_as_captain(client)
    response = client.post("/api/dishes", json={"name": "Bad Dish"})
    assert response.status_code == 400
    logout(client)


# Проверяем: ошибка при создании блюда с дублирующимся именем
def test_create_dish_duplicate_name(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    payload = {
        "name": "Test Dish",
        "ingredients": "Something",
        "url": "https://youtube.com/watch?v=1"
    }
    response = client.post("/api/dishes", json=payload)
    assert response.status_code == 400

    session = db_session.create_session()
    dish = session.query(Dish).get(dish_id)
    session.delete(dish)
    session.commit()
    session.close()
    logout(client)
    dell_test_dish()


# Проверяем: ошибка при создании блюда с некорректной ссылкой (не YouTube)
def test_create_dish_invalid_url(client):
    login_as_captain(client)
    payload = {
        "name": "Bad URL Dish",
        "ingredients": "X",
        "url": "https://google.com"
    }
    response = client.post("/api/dishes", json=payload)
    assert response.status_code == 400
    logout(client)


# =====================================================
# 3. ОБНОВЛЕНИЕ БЛЮДА
# =====================================================
# Проверяем: корректное обновление блюда авторизованным пользователем
def test_update_dish_correct(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    payload = {"name": "Updated Dish"}
    response = client.put(f"/api/dishes/{dish_id}", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["dish"]["name"] == "Updated Dish"

    session = db_session.create_session()
    dish = session.query(Dish).get(dish_id)
    session.delete(dish)
    session.commit()
    session.close()
    logout(client)
    dell_test_dish()


# Проверяем: попытка обновления несуществующего блюда
def test_update_dish_not_found(client):
    login_as_captain(client)
    response = client.put("/api/dishes/999999", json={"name": "No Dish"})
    assert response.status_code == 404
    logout(client)


# Проверяем: запрет обновления блюда неавторизованным пользователем
def test_update_dish_permission_denied(client):
    dish_id = create_test_dish()
    response = client.put(f"/api/dishes/{dish_id}", json={"name": "Hack"})
    assert response.status_code == 401 or response.status_code == 403
    dell_test_dish()


# =====================================================
# 4. УДАЛЕНИЕ БЛЮДА
# =====================================================
# Проверяем: корректное удаление блюда администратором
def test_delete_dish_correct(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    response = client.delete(f"/api/dishes/{dish_id}")
    assert response.status_code == 200
    logout(client)
    dell_test_dish()


# Проверяем: попытка удаления несуществующего блюда
def test_delete_dish_not_found(client):
    login_as_captain(client)
    response = client.delete("/api/dishes/999999")
    assert response.status_code == 404
    logout(client)


# =====================================================
# 5. РЕЙТИНГИ
# =====================================================
# Проверяем: корректную установку рейтинга блюда
def test_rate_dish_correct(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    response = client.post(
        f"/api/dishes/{dish_id}/rate",
        json={"rating": 5}
    )
    assert response.status_code == 200
    assert response.get_json()["rating"] == 5

    logout(client)
    dell_test_dish()


# Проверяем: ошибка при передаче некорректного значения рейтинга
def test_rate_dish_invalid_value(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    response = client.post(
        f"/api/dishes/{dish_id}/rate",
        json={"rating": 10}
    )
    assert response.status_code == 400
    logout(client)
    dell_test_dish()


# Проверяем: получение рейтинга текущего пользователя
def test_get_user_rating(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    client.post(f"/api/dishes/{dish_id}/rate", json={"rating": 4})
    response = client.get(f"/api/dishes/{dish_id}/rating")
    assert response.status_code == 200
    assert response.get_json()["rating"] == 4

    logout(client)
    dell_test_dish()


# =====================================================
# 6. ИЗБРАННОЕ
# =====================================================
# Проверяем: добавление и удаление блюда из избранного
def test_toggle_favourite(client):
    login_as_captain(client)
    dish_id = create_test_dish()

    response = client.post(f"/api/dishes/{dish_id}/favourite")
    assert response.status_code == 200
    assert response.get_json()["is_favourite"] is True

    response = client.post(f"/api/dishes/{dish_id}/favourite")
    assert response.get_json()["is_favourite"] is False

    logout(client)
    dell_test_dish()


# Проверяем: получение списка избранных блюд пользователя
def test_get_user_favourites(client):
    login_as_captain(client)
    dish_id = create_test_dish()
    client.post(f"/api/dishes/{dish_id}/favourite")

    response = client.get("/api/user/favourites")
    assert response.status_code == 200
    data = response.get_json()
    assert data["count"] >= 1

    logout(client)
    dell_test_dish()
