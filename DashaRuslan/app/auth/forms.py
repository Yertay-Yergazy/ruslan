from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length, ValidationError, Optional
from app.models import User


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    remember_me = BooleanField('Запомнить меня')
    submit = SubmitField('Войти')


class RegisterForm(FlaskForm):
    first_name = StringField('Имя', validators=[DataRequired(), Length(2, 50)])
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(2, 50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[Optional(), Length(max=20)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    password2 = PasswordField('Подтвердите пароль',
                               validators=[DataRequired(), EqualTo('password', message='Пароли не совпадают')])
    submit = SubmitField('Зарегистрироваться')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            raise ValidationError('Этот email уже зарегистрирован.')


class ProfileForm(FlaskForm):
    first_name = StringField('Имя', validators=[DataRequired(), Length(2, 50)])
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(2, 50)])
    phone = StringField('Телефон', validators=[Optional(), Length(max=20)])
    submit = SubmitField('Сохранить')


class ChangePasswordForm(FlaskForm):
    old_password = PasswordField('Текущий пароль', validators=[DataRequired()])
    new_password = PasswordField('Новый пароль', validators=[DataRequired(), Length(min=6)])
    new_password2 = PasswordField('Подтвердите новый пароль',
                                   validators=[DataRequired(), EqualTo('new_password', message='Пароли не совпадают')])
    submit = SubmitField('Изменить пароль')
