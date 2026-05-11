from flask_wtf import FlaskForm
from wtforms import (StringField, TextAreaField, SelectField, DateField,
                     HiddenField, IntegerField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange


class BookingForm(FlaskForm):
    service_id = HiddenField('Услуга', validators=[DataRequired()])
    employee_id = SelectField('Мастер', coerce=int, validators=[DataRequired()])
    booking_date = DateField('Дата', validators=[DataRequired()])
    start_time = HiddenField('Время', validators=[DataRequired()])
    car_info = StringField('Информация об автомобиле (марка, модель, год)',
                           validators=[Optional(), Length(max=200)])
    notes = TextAreaField('Дополнительные пожелания', validators=[Optional(), Length(max=500)])
    submit = SubmitField('Подтвердить запись')


class ReviewForm(FlaskForm):
    rating = HiddenField('Оценка', validators=[DataRequired()])
    comment = TextAreaField('Ваш отзыв', validators=[Optional(), Length(max=1000)])
    submit = SubmitField('Отправить отзыв')
