from datetime import datetime, date, time, timedelta
from flask import render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from sqlalchemy import func
from app.client import bp
from app.client.forms import BookingForm, ReviewForm
from app.models import (db, ServiceCategory, Service, Employee,
                         Booking, Review, WorkSchedule)
from app.utils import generate_booking_number, get_time_slots, is_slot_available


@bp.route('/')
def index():
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.sort_order).all()
    featured_services = Service.query.filter_by(is_active=True, is_featured=True).limit(6).all()
    employees = (Employee.query.filter_by(is_available=True)
                 .join(Employee.user).limit(4).all())
    reviews = (Review.query.filter_by(is_published=True)
               .order_by(Review.created_at.desc()).limit(6).all())
    stats = {
        'total_bookings': Booking.query.filter_by(status='completed').count(),
        'total_clients': db.session.query(func.count(func.distinct(Booking.client_id))).scalar() or 0,
        'total_employees': Employee.query.filter_by(is_available=True).count(),
        'avg_rating': db.session.query(func.avg(Review.rating)).filter_by(is_published=True).scalar()
    }
    if stats['avg_rating']:
        stats['avg_rating'] = round(stats['avg_rating'], 1)
    return render_template('client/index.html', title='Главная',
                           categories=categories,
                           featured_services=featured_services,
                           employees=employees,
                           reviews=reviews,
                           stats=stats)


@bp.route('/services')
def services():
    cat_slug = request.args.get('category', '')
    search = request.args.get('search', '')

    query = Service.query.filter_by(is_active=True)
    categories = ServiceCategory.query.filter_by(is_active=True).order_by(ServiceCategory.sort_order).all()
    current_category = None

    if cat_slug:
        cat = ServiceCategory.query.filter_by(slug=cat_slug, is_active=True).first()
        if cat:
            query = query.filter_by(category_id=cat.id)
            current_category = cat

    if search:
        query = query.filter(
            Service.name.ilike(f'%{search}%') | Service.description.ilike(f'%{search}%')
        )

    services_list = query.order_by(Service.name).all()
    return render_template('client/services.html',
                           title='Услуги',
                           services=services_list,
                           categories=categories,
                           current_category=current_category,
                           search=search)


@bp.route('/services/<int:service_id>')
def service_detail(service_id):
    service = Service.query.filter_by(id=service_id, is_active=True).first_or_404()
    # Employees that provide this service
    employees = [e for e in service.employees if e.is_available]
    reviews = (Review.query
               .join(Booking, Review.booking_id == Booking.id)
               .filter(Booking.service_id == service_id, Review.is_published == True)
               .order_by(Review.created_at.desc())
               .limit(5).all())
    return render_template('client/service_detail.html',
                           title=service.name,
                           service=service,
                           employees=employees,
                           reviews=reviews)


@bp.route('/booking', methods=['GET', 'POST'])
@login_required
def booking():
    service_id = request.args.get('service_id', type=int)
    employee_id_param = request.args.get('employee_id', type=int)

    service = None
    preselected_employee = None
    form = BookingForm()
    selected_service_id = request.form.get('service_id', type=int) if request.method == 'POST' else service_id
    initial_step = 1

    if employee_id_param:
        preselected_employee = Employee.query.filter_by(id=employee_id_param, is_available=True).first()

    if selected_service_id:
        service = Service.query.filter_by(id=selected_service_id, is_active=True).first()
        if not service and request.method == 'GET':
            abort(404)

    # Build employee choices
    if service:
        available_employees = [e for e in service.employees if e.is_available]
    else:
        available_employees = [preselected_employee] if preselected_employee else Employee.query.filter_by(is_available=True).all()

    form.employee_id.choices = [
        (e.id, f"{e.user.full_name} — {e.specialization or 'Мастер'}")
        for e in available_employees
    ]
    if not form.employee_id.choices:
        form.employee_id.choices = [(-1, 'Нет доступных мастеров')]

    if form.validate_on_submit():
        emp = Employee.query.get(form.employee_id.data)
        svc = Service.query.get(int(form.service_id.data))
        if not emp or not svc or not svc.is_active or not emp.is_available:
            flash('Ошибка выбора мастера или услуги.', 'danger')
            return redirect(url_for('client.booking'))

        if svc not in emp.services:
            flash('Выбранный мастер не выполняет эту услугу. Пожалуйста, выберите другого мастера.', 'danger')
            return redirect(url_for('client.booking', service_id=svc.id))

        booking_date = form.booking_date.data
        if booking_date < date.today():
            flash('Нельзя записаться на прошедшую дату.', 'danger')
            return redirect(url_for('client.booking', service_id=svc.id))

        try:
            start_time_obj = datetime.strptime(form.start_time.data, '%H:%M').time()
        except ValueError:
            flash('Неверный формат времени.', 'danger')
            return redirect(url_for('client.booking', service_id=svc.id))

        if not is_slot_available(emp.id, booking_date, start_time_obj, svc.duration):
            flash('Выбранное время уже занято. Пожалуйста, выберите другое.', 'warning')
            return redirect(url_for('client.booking', service_id=svc.id))

        end_time_obj = (datetime.combine(booking_date, start_time_obj) +
                        timedelta(minutes=svc.duration)).time()

        new_booking = Booking(
            booking_number=generate_booking_number(),
            client_id=current_user.id,
            employee_id=emp.id,
            service_id=svc.id,
            booking_date=booking_date,
            start_time=start_time_obj,
            end_time=end_time_obj,
            total_price=svc.price,
            car_info=form.car_info.data,
            notes=form.notes.data,
            status=Booking.STATUS_PENDING
        )
        db.session.add(new_booking)
        db.session.commit()

        flash('Запись успешно создана! Ожидайте подтверждения.', 'success')
        return redirect(url_for('client.booking_success', booking_id=new_booking.id))
    elif request.method == 'POST':
        missing_labels = {
            'service_id': 'услугу',
            'employee_id': 'мастера',
            'booking_date': 'дату',
            'start_time': 'время'
        }
        missing = [label for field, label in missing_labels.items() if field in form.errors]
        if missing:
            flash(f"Проверьте выбранные данные записи: выберите {', '.join(missing)}.", 'danger')
        else:
            flash('Не удалось создать запись. Проверьте данные формы и попробуйте ещё раз.', 'danger')
        if 'service_id' in form.errors:
            initial_step = 1
        elif 'employee_id' in form.errors:
            initial_step = 2
        elif 'booking_date' in form.errors or 'start_time' in form.errors:
            initial_step = 3
        else:
            initial_step = 4

    # Pre-fill
    if service and request.method == 'GET':
        form.service_id.data = str(service.id)
    can_preselect_employee = preselected_employee and (not service or preselected_employee in available_employees)
    if can_preselect_employee and request.method == 'GET':
        form.employee_id.data = employee_id_param
    elif service and preselected_employee and preselected_employee not in available_employees:
        preselected_employee = None

    # Get all active services for selector
    if preselected_employee and not service:
        all_services = sorted([s for s in preselected_employee.services if s.is_active], key=lambda s: s.name)
    else:
        all_services = Service.query.filter_by(is_active=True).order_by(Service.name).all()

    return render_template('client/booking.html',
                           title='Запись на услугу',
                           form=form,
                           service=service,
                           all_services=all_services,
                           available_employees=available_employees,
                           initial_step=initial_step,
                           preselected_employee=preselected_employee)


@bp.route('/booking/success/<int:booking_id>')
@login_required
def booking_success(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.client_id != current_user.id:
        abort(403)
    return render_template('client/booking_success.html',
                           title='Запись создана',
                           booking=booking)


@bp.route('/my-bookings')
@login_required
def my_bookings():
    status = request.args.get('status', '')
    query = Booking.query.filter_by(client_id=current_user.id)
    if status:
        query = query.filter_by(status=status)
    bookings_list = query.order_by(Booking.booking_date.desc(), Booking.start_time.desc()).all()
    return render_template('client/my_bookings.html',
                           title='Мои записи',
                           bookings=bookings_list,
                           current_status=status)


@bp.route('/my-bookings/<int:booking_id>')
@login_required
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.client_id != current_user.id:
        abort(403)
    review_form = ReviewForm() if booking.can_review() else None
    return render_template('client/booking_detail.html',
                           title=f'Запись #{booking.booking_number}',
                           booking=booking,
                           review_form=review_form)


@bp.route('/my-bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
def booking_cancel(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.client_id != current_user.id:
        abort(403)
    if not booking.can_cancel():
        flash('Невозможно отменить эту запись.', 'danger')
    else:
        booking.status = Booking.STATUS_CANCELLED
        booking.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Запись отменена.', 'info')
    return redirect(url_for('client.booking_detail', booking_id=booking_id))


@bp.route('/my-bookings/<int:booking_id>/review', methods=['POST'])
@login_required
def booking_review(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    if booking.client_id != current_user.id:
        abort(403)
    if not booking.can_review():
        flash('Нельзя оставить отзыв для этой записи.', 'danger')
        return redirect(url_for('client.booking_detail', booking_id=booking_id))

    form = ReviewForm()
    if form.validate_on_submit():
        try:
            rating = int(form.rating.data)
            if not 1 <= rating <= 5:
                raise ValueError
        except (ValueError, TypeError):
            flash('Укажите оценку от 1 до 5.', 'danger')
            return redirect(url_for('client.booking_detail', booking_id=booking_id))

        review = Review(
            booking_id=booking.id,
            client_id=current_user.id,
            rating=rating,
            comment=form.comment.data
        )
        db.session.add(review)
        db.session.commit()
        flash('Спасибо за ваш отзыв!', 'success')
    else:
        flash('Укажите оценку от 1 до 5 перед отправкой отзыва.', 'warning')
    return redirect(url_for('client.booking_detail', booking_id=booking_id))


@bp.route('/employees')
def employees():
    employees_list = (Employee.query.filter_by(is_available=True)
                      .join(Employee.user)
                      .order_by(Employee.user_id)
                      .all())
    return render_template('client/employees.html', title='Наши мастера', employees=employees_list)


@bp.route('/about')
def about():
    return render_template('client/about.html', title='О нас')


@bp.route('/contacts', methods=['GET', 'POST'])
def contacts():
    if request.method == 'POST':
        name = (request.form.get('name') or '').strip()
        phone = (request.form.get('phone') or '').strip()
        email = (request.form.get('email') or '').strip()
        message = (request.form.get('message') or '').strip()
        if not name or not (phone or email) or not message:
            flash('Заполните имя, сообщение и хотя бы один контакт для связи.', 'warning')
        else:
            flash('Сообщение отправлено! Мы свяжемся с вами в ближайшее время.', 'success')
        return redirect(url_for('client.contacts'))
    return render_template('client/contacts.html', title='Контакты')
