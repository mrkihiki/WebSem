from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SubmitField
from wtforms.validators import DataRequired, URL, Optional


class AddDishForm(FlaskForm):
    name = StringField('Название блюда', validators=[DataRequired()])
    ingredients = TextAreaField('Ингредиенты', validators=[DataRequired()])
    url = StringField('URL видео (YouTube)',
                      validators=[Optional(), URL(message='Пожалуйста, введите корректную ссылку на YouTube видео')])
    submit = SubmitField('Сохранить')

    @staticmethod
    def is_youtube_link(url):
        return "youtube.com" in url or "youtu.be" in url
