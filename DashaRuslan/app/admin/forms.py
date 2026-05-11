from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import (StringField, TextAreaField, DecimalField, IntegerField,
                     BooleanField, SelectField, SelectMultipleField, SubmitField,
                     PasswordField, TimeField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange, Email, ValidationError
from app.models import User


class ServiceCategoryForm(FlaskForm):
    name = StringField('Название', validators=[DataRequired(), Length(2, 100)])
    description = TextAreaField('Описание', validators=[Optional()])
    icon = StringField('Font Awesome иконка (fa-...)', validators=[Optional(), Length(max=50)])
    slug = StringField('Slug (URL)', validators=[DataRequired(), Length(2, 100)])
    sort_order = IntegerField('Порядок сортировки', validators=[Optional()], default=0)
    is_active = BooleanField('Активна')
    submit = SubmitField('Сохранить')


class ServiceForm(FlaskForm):
    name = StringField('Название услуги', validators=[DataRequired(), Length(2, 200)])
    short_description = StringField('Краткое описание', validators=[Optional(), Length(max=300)])
    description = TextAreaField('Полное описание', validators=[Optional()])
    price = DecimalField('Цена (₸)', validators=[DataRequired(), NumberRange(min=0)], places=2)
    duration = IntegerField('Длительность (мин)', validators=[DataRequired(), NumberRange(min=15, max=480)])
    category_id = SelectField('Категория', coerce=int, validators=[DataRequired()])
    image = FileField('Изображение', validators=[Optional(),
                                                  FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Только изображения')])
    is_active = BooleanField('Активна')
    is_featured = BooleanField('Рекомендуемая')
    submit = SubmitField('Сохранить')


class EmployeeForm(FlaskForm):
    # User fields
    first_name = StringField('Имя', validators=[DataRequired(), Length(2, 50)])
    last_name = StringField('Фамилия', validators=[DataRequired(), Length(2, 50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    phone = StringField('Телефон', validators=[Optional(), Length(max=20)])
    password = PasswordField('Пароль (оставьте пустым для сохранения текущего)',
                              validators=[Optional(), Length(min=6)])

    # Employee fields
    specialization = StringField('Специализация', validators=[Optional(), Length(max=200)])
    bio = TextAreaField('О мастере', validators=[Optional()])
    experience_years = IntegerField('Опыт (лет)', validators=[Optional(), NumberRange(min=0, max=60)], default=0)
    photo = FileField('Фото', validators=[Optional(),
                                           FileAllowed(['jpg', 'jpeg', 'png', 'gif', 'webp'], 'Только изображения')])
    is_available = BooleanField('Доступен для записи')
    services = SelectMultipleField('Услуги', coerce=int, validators=[Optional()])
    submit = SubmitField('Сохранить')

    def __init__(self, employee_id=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.employee_id = employee_id

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data.lower()).first()
        if user:
            # Allow if it's the same employee's user
            if self.employee_id:
                from app.models import Employee
                emp = Employee.query.get(self.employee_id)
                if emp and emp.user.email == email.data.lower():
                    return
            raise ValidationError('Этот email уже зарегистрирован.')


class WorkScheduleForm(FlaskForm):
    # 7 days schedule
    mon_working = BooleanField('Понедельник')
    mon_start = TimeField('Начало', validators=[Optional()])
    mon_end = TimeField('Конец', validators=[Optional()])

    tue_working = BooleanField('Вторник')
    tue_start = TimeField('Начало', validators=[Optional()])
    tue_end = TimeField('Конец', validators=[Optional()])

    wed_working = BooleanField('Среда')
    wed_start = TimeField('Начало', validators=[Optional()])
    wed_end = TimeField('Конец', validators=[Optional()])

    thu_working = BooleanField('Четверг')
    thu_start = TimeField('Начало', validators=[Optional()])
    thu_end = TimeField('Конец', validators=[Optional()])

    fri_working = BooleanField('Пятница')
    fri_start = TimeField('Начало', validators=[Optional()])
    fri_end = TimeField('Конец', validators=[Optional()])

    sat_working = BooleanField('Суббота')
    sat_start = TimeField('Начало', validators=[Optional()])
    sat_end = TimeField('Конец', validators=[Optional()])

    sun_working = BooleanField('Воскресенье')
    sun_start = TimeField('Начало', validators=[Optional()])
    sun_end = TimeField('Конец', validators=[Optional()])

    submit = SubmitField('Сохранить расписание')


class BookingStatusForm(FlaskForm):
    status = SelectField('Статус', choices=[
        ('pending', 'Ожидает подтверждения'),
        ('confirmed', 'Подтверждено'),
        ('in_progress', 'В работе'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
    ], validators=[DataRequired()])
    admin_notes = TextAreaField('Заметки администратора', validators=[Optional()])
    submit = SubmitField('Обновить статус')
