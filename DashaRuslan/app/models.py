from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='client')  # admin, employee, client
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(20))
    avatar = db.Column(db.String(255), default='default_avatar.png')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    employee_profile = db.relationship('Employee', back_populates='user', uselist=False)
    bookings = db.relationship('Booking', foreign_keys='Booking.client_id', back_populates='client')
    reviews = db.relationship('Review', back_populates='author')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    def is_admin(self):
        return self.role == 'admin'

    def is_employee_role(self):
        return self.role == 'employee'

    def is_client(self):
        return self.role == 'client'

    def __repr__(self):
        return f'<User {self.email}>'


class ServiceCategory(db.Model):
    __tablename__ = 'service_categories'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='fa-wrench')
    slug = db.Column(db.String(100), unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    sort_order = db.Column(db.Integer, default=0)

    services = db.relationship('Service', back_populates='category', lazy='dynamic')

    def __repr__(self):
        return f'<ServiceCategory {self.name}>'


class Service(db.Model):
    __tablename__ = 'services'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    short_description = db.Column(db.String(300))
    price = db.Column(db.Numeric(10, 2), nullable=False)
    duration = db.Column(db.Integer, nullable=False)  # minutes
    category_id = db.Column(db.Integer, db.ForeignKey('service_categories.id'), nullable=False)
    image = db.Column(db.String(255), default='default_service.jpg')
    is_active = db.Column(db.Boolean, default=True)
    is_featured = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    category = db.relationship('ServiceCategory', back_populates='services')
    bookings = db.relationship('Booking', back_populates='service')

    @property
    def duration_display(self):
        hours = self.duration // 60
        minutes = self.duration % 60
        if hours and minutes:
            return f"{hours} ч {minutes} мин"
        elif hours:
            return f"{hours} ч"
        else:
            return f"{minutes} мин"

    def __repr__(self):
        return f'<Service {self.name}>'


# Association table for Employee <-> Service
employee_services = db.Table(
    'employee_services',
    db.Column('employee_id', db.Integer, db.ForeignKey('employees.id'), primary_key=True),
    db.Column('service_id', db.Integer, db.ForeignKey('services.id'), primary_key=True)
)


class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    specialization = db.Column(db.String(200))
    bio = db.Column(db.Text)
    experience_years = db.Column(db.Integer, default=0)
    photo = db.Column(db.String(255), default='default_employee.jpg')
    is_available = db.Column(db.Boolean, default=True)

    user = db.relationship('User', back_populates='employee_profile')
    services = db.relationship('Service', secondary='employee_services', backref='employees')
    bookings = db.relationship('Booking', foreign_keys='Booking.employee_id', back_populates='employee')
    schedules = db.relationship('WorkSchedule', back_populates='employee', cascade='all, delete-orphan')

    @property
    def avg_rating(self):
        ratings = [b.review.rating for b in self.bookings if b.review and b.review.is_published]
        if ratings:
            return round(sum(ratings) / len(ratings), 1)
        return None

    @property
    def reviews_count(self):
        return sum(1 for b in self.bookings if b.review and b.review.is_published)

    def __repr__(self):
        return f'<Employee {self.user.full_name}>'


class WorkSchedule(db.Model):
    __tablename__ = 'work_schedules'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    day_of_week = db.Column(db.Integer, nullable=False)  # 0=Mon, 6=Sun
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    is_working = db.Column(db.Boolean, default=True)

    employee = db.relationship('Employee', back_populates='schedules')

    DAY_NAMES = {
        0: 'Понедельник', 1: 'Вторник', 2: 'Среда',
        3: 'Четверг', 4: 'Пятница', 5: 'Суббота', 6: 'Воскресенье'
    }
    DAY_NAMES_SHORT = {
        0: 'Пн', 1: 'Вт', 2: 'Ср', 3: 'Чт', 4: 'Пт', 5: 'Сб', 6: 'Вс'
    }

    @property
    def day_name(self):
        return self.DAY_NAMES.get(self.day_of_week, '')

    @property
    def day_name_short(self):
        return self.DAY_NAMES_SHORT.get(self.day_of_week, '')

    def __repr__(self):
        return f'<WorkSchedule {self.day_name} {self.start_time}-{self.end_time}>'


class Booking(db.Model):
    __tablename__ = 'bookings'

    STATUS_PENDING = 'pending'
    STATUS_CONFIRMED = 'confirmed'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_CANCELLED = 'cancelled'

    STATUS_CHOICES = {
        STATUS_PENDING: 'Ожидает подтверждения',
        STATUS_CONFIRMED: 'Подтверждено',
        STATUS_IN_PROGRESS: 'В работе',
        STATUS_COMPLETED: 'Завершено',
        STATUS_CANCELLED: 'Отменено'
    }

    STATUS_BADGE = {
        STATUS_PENDING: 'warning',
        STATUS_CONFIRMED: 'info',
        STATUS_IN_PROGRESS: 'primary',
        STATUS_COMPLETED: 'success',
        STATUS_CANCELLED: 'danger'
    }

    id = db.Column(db.Integer, primary_key=True)
    booking_number = db.Column(db.String(20), unique=True)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    service_id = db.Column(db.Integer, db.ForeignKey('services.id'), nullable=False)
    booking_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    status = db.Column(db.String(20), default=STATUS_PENDING)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    notes = db.Column(db.Text)
    car_info = db.Column(db.String(200))
    admin_notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    client = db.relationship('User', foreign_keys=[client_id], back_populates='bookings')
    employee = db.relationship('Employee', foreign_keys=[employee_id], back_populates='bookings')
    service = db.relationship('Service', back_populates='bookings')
    review = db.relationship('Review', back_populates='booking', uselist=False)

    @property
    def status_display(self):
        return self.STATUS_CHOICES.get(self.status, self.status)

    @property
    def status_badge(self):
        return self.STATUS_BADGE.get(self.status, 'secondary')

    def can_cancel(self):
        return self.status in (self.STATUS_PENDING, self.STATUS_CONFIRMED)

    def can_review(self):
        return self.status == self.STATUS_COMPLETED and not self.review

    def __repr__(self):
        return f'<Booking #{self.booking_number}>'


class Review(db.Model):
    __tablename__ = 'reviews'

    id = db.Column(db.Integer, primary_key=True)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), unique=True, nullable=False)
    client_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    comment = db.Column(db.Text)
    is_published = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    booking = db.relationship('Booking', back_populates='review')
    author = db.relationship('User', back_populates='reviews')

    def __repr__(self):
        return f'<Review {self.rating}★>'
