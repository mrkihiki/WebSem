from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from urllib.parse import urlparse

from data import db_session
from data.users import User
from forms.login import LoginForm, RegisterForm

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dishes.dishes_list'))

    form = LoginForm()
    if form.validate_on_submit():
        session = db_session.create_session()
        user = session.query(User).filter(User.login == form.login.data).first()

        if user is None or not user.check_password(form.password.data):
            flash('Неверный логин или пароль', 'danger')
            session.close()
            return redirect(url_for('auth.login'))

        login_user(user, remember=form.remember_me.data)
        flash(f'Добро пожаловать, {user.login}!', 'success')
        session.close()

        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('dishes.dishes_list')
        return redirect(next_page)

    return render_template('login.html',
                           title='Вход',
                           form=form,
                           get_navbar=get_navbar(),
                           get_footer=get_footer())


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dishes.dishes_list'))

    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_confirm.data:
            flash('Пароли не совпадают', 'danger')
            return redirect(url_for('auth.register'))

        session = db_session.create_session()
        existing_user = session.query(User).filter(User.login == form.login.data).first()

        if existing_user:
            flash('Пользователь с таким логином уже существует', 'danger')
            session.close()
            return redirect(url_for('auth.register'))

        user = User(login=form.login.data)
        user.set_password(form.password.data)

        session.add(user)
        session.commit()
        session.close()

        flash('Регистрация успешна! Теперь вы можете войти.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html',
                           title='Регистрация',
                           form=form,
                           get_navbar=get_navbar(),
                           get_footer=get_footer())


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы вышли из системы', 'info')
    return redirect(url_for('index'))


# Вспомогательные функции для шаблонов
def get_navbar():
    from app import get_navbar as app_get_navbar
    return app_get_navbar()


def get_footer():
    from app import get_footer as app_get_footer
    return app_get_footer()
