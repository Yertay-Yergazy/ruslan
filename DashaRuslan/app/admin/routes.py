from datetime import datetime, date, time, timedelta
from flask import render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import func, extract
from app.admin import bp
from app.admin.forms import (ServiceCategoryForm, ServiceForm, EmployeeForm,
                              WorkScheduleForm, BookingStatusForm)
from app.models import (db, User, ServiceCategory, Service, Employee,
                         WorkSchedule, Booking, Review)
from app.utils import admin_required, save_image
from slugify import slugify


# ─────────────────────────── Dashboard ───────────────────────────

@bp.route('/')
@bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    today = date.today()
    month_start = today.replace(day=1)

    stats = {
        'total_bookings': Booking.query.count(),
        'today_bookings': Booking.query.filter_by(booking_date=today).count(),
        'month_bookings': Booking.query.filter(Booking.booking_date >= month_start).count(),
        'pending_bookings': Booking.query.filter_by(status='pending').count(),
        'total_clients': User.query.filter_by(role='client').count(),
        'total_employees': Employee.query.count(),
        'total_services': Service.query.filter_by(is_active=True).count(),
        'total_revenue': db.session.query(func.sum(Booking.total_price))
                          .filter_by(status='completed').scalar() or 0,
        'month_revenue': db.session.query(func.sum(Booking.total_price))
                          .filter(Booking.status == 'completed',
                                  Booking.booking_date >= month_start).scalar() or 0,
    }

    # Recent bookings
    recent_bookings = (Booking.query
                       .order_by(Booking.created_at.desc())
                       .limit(8).all())

    # Today's bookings
    today_bookings = (Booking.query
                      .filter_by(booking_date=today)
                      .filter(Booking.status.in_(['confirmed', 'in_progress', 'pending']))
                      .order_by(Booking.start_time)
                      .all())

    # Monthly revenue chart data (last 6 months)
    chart_data = []
    for i in range(5, -1, -1):
        d = today - timedelta(days=today.day - 1) - timedelta(days=30 * i)
        m_start = d.replace(day=1)
        if i == 0:
            m_end = today
        else:
            next_month = (m_start.replace(month=m_start.month % 12 + 1)
                          if m_start.month < 12 else m_start.replace(year=m_start.year + 1, month=1))
            m_end = next_month - timedelta(days=1)
        rev = db.session.query(func.sum(Booking.total_price)).filter(
            Booking.status == 'completed',
            Booking.booking_date >= m_start,
            Booking.booking_date <= m_end
        ).scalar() or 0
        chart_data.append({
            'month': m_start.strftime('%b %Y'),
            'revenue': float(rev)
        })

    # Bookings by status
    status_data = db.session.query(Booking.status, func.count(Booking.id)).group_by(Booking.status).all()
    status_chart = {row[0]: row[1] for row in status_data}

    return render_template('admin/dashboard.html',
                           title='Панель управления',
                           stats=stats,
                           recent_bookings=recent_bookings,
                           today_bookings=today_bookings,
                           chart_data=chart_data,
                           status_chart=status_chart)


# ─────────────────────────── Bookings ───────────────────────────

@bp.route('/bookings')
@login_required
@admin_required
def bookings():
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    date_str = request.args.get('date', '')
    search = request.args.get('search', '')

    query = Booking.query

    if status:
        query = query.filter_by(status=status)
    if date_str:
        try:
            filter_date = datetime.strptime(date_str, '%Y-%m-%d').date()
            query = query.filter_by(booking_date=filter_date)
        except ValueError:
            pass
    if search:
        query = query.join(User, Booking.client_id == User.id).filter(
            (User.first_name + ' ' + User.last_name).ilike(f'%{search}%')
            | User.phone.ilike(f'%{search}%')
            | User.email.ilike(f'%{search}%')
            | Booking.booking_number.ilike(f'%{search}%')
            | Booking.car_info.ilike(f'%{search}%')
        )

    bookings_list = (query.order_by(Booking.booking_date.desc(), Booking.start_time.desc())
                     .paginate(page=page, per_page=20, error_out=False))

    return render_template('admin/bookings/index.html',
                           title='Записи',
                           bookings=bookings_list,
                           current_status=status,
                           current_date=date_str,
                           search=search)


@bp.route('/bookings/<int:booking_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def booking_detail(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    form = BookingStatusForm(obj=booking)
    if form.validate_on_submit():
        booking.status = form.status.data
        booking.admin_notes = form.admin_notes.data
        booking.updated_at = datetime.utcnow()
        db.session.commit()
        flash('Статус записи обновлён.', 'success')
        return redirect(url_for('admin.booking_detail', booking_id=booking.id))
    form.status.data = booking.status
    form.admin_notes.data = booking.admin_notes
    return render_template('admin/bookings/detail.html',
                           title=f'Запись #{booking.booking_number}',
                           booking=booking, form=form)


# ─────────────────────────── Services ───────────────────────────

@bp.route('/services')
@login_required
@admin_required
def services():
    cat_id = request.args.get('category', 0, type=int)
    query = Service.query
    if cat_id:
        query = query.filter_by(category_id=cat_id)
    services_list = query.order_by(Service.created_at.desc()).all()
    categories = ServiceCategory.query.order_by(ServiceCategory.sort_order).all()
    return render_template('admin/services/index.html',
                           title='Услуги',
                           services=services_list,
                           categories=categories,
                           current_category=cat_id)


@bp.route('/services/new', methods=['GET', 'POST'])
@login_required
@admin_required
def service_new():
    form = ServiceForm()
    form.category_id.choices = [(c.id, c.name) for c in ServiceCategory.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        service = Service(
            name=form.name.data.strip(),
            short_description=form.short_description.data,
            description=form.description.data,
            price=form.price.data,
            duration=form.duration.data,
            category_id=form.category_id.data,
            is_active=form.is_active.data,
            is_featured=form.is_featured.data
        )
        if form.image.data and form.image.data.filename:
            filename = save_image(form.image.data, 'services')
            if filename:
                service.image = filename
        db.session.add(service)
        db.session.commit()
        flash('Услуга создана.', 'success')
        return redirect(url_for('admin.services'))
    form.is_active.data = True
    return render_template('admin/services/form.html', title='Новая услуга', form=form)


@bp.route('/services/<int:service_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def service_edit(service_id):
    service = Service.query.get_or_404(service_id)
    form = ServiceForm(obj=service)
    form.category_id.choices = [(c.id, c.name) for c in ServiceCategory.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        service.name = form.name.data.strip()
        service.short_description = form.short_description.data
        service.description = form.description.data
        service.price = form.price.data
        service.duration = form.duration.data
        service.category_id = form.category_id.data
        service.is_active = form.is_active.data
        service.is_featured = form.is_featured.data
        if form.image.data and form.image.data.filename:
            filename = save_image(form.image.data, 'services')
            if filename:
                service.image = filename
        db.session.commit()
        flash('Услуга обновлена.', 'success')
        return redirect(url_for('admin.services'))
    return render_template('admin/services/form.html', title='Редактировать услугу',
                           form=form, service=service)


@bp.route('/services/<int:service_id>/delete', methods=['POST'])
@login_required
@admin_required
def service_delete(service_id):
    service = Service.query.get_or_404(service_id)
    if service.bookings:
        service.is_active = False
        db.session.commit()
        flash('Услуга деактивирована (есть связанные записи).', 'warning')
    else:
        db.session.delete(service)
        db.session.commit()
        flash('Услуга удалена.', 'success')
    return redirect(url_for('admin.services'))


# ─────────────────────────── Categories ───────────────────────────

@bp.route('/categories')
@login_required
@admin_required
def categories():
    cats = ServiceCategory.query.order_by(ServiceCategory.sort_order).all()
    return render_template('admin/services/categories.html', title='Категории услуг', categories=cats)


@bp.route('/categories/new', methods=['GET', 'POST'])
@login_required
@admin_required
def category_new():
    form = ServiceCategoryForm()
    if form.validate_on_submit():
        slug = form.slug.data.strip() or slugify(form.name.data)
        cat = ServiceCategory(
            name=form.name.data.strip(),
            description=form.description.data,
            icon=form.icon.data.strip() or 'fa-wrench',
            slug=slug,
            sort_order=form.sort_order.data or 0,
            is_active=form.is_active.data
        )
        db.session.add(cat)
        db.session.commit()
        flash('Категория создана.', 'success')
        return redirect(url_for('admin.categories'))
    form.is_active.data = True
    return render_template('admin/services/category_form.html', title='Новая категория', form=form)


@bp.route('/categories/<int:cat_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def category_edit(cat_id):
    cat = ServiceCategory.query.get_or_404(cat_id)
    form = ServiceCategoryForm(obj=cat)
    if form.validate_on_submit():
        cat.name = form.name.data.strip()
        cat.description = form.description.data
        cat.icon = form.icon.data.strip() or 'fa-wrench'
        cat.slug = form.slug.data.strip() or slugify(form.name.data)
        cat.sort_order = form.sort_order.data or 0
        cat.is_active = form.is_active.data
        db.session.commit()
        flash('Категория обновлена.', 'success')
        return redirect(url_for('admin.categories'))
    return render_template('admin/services/category_form.html', title='Редактировать категорию',
                           form=form, category=cat)


@bp.route('/categories/<int:cat_id>/delete', methods=['POST'])
@login_required
@admin_required
def category_delete(cat_id):
    cat = ServiceCategory.query.get_or_404(cat_id)
    if cat.services.count() > 0:
        flash('Нельзя удалить категорию с услугами.', 'danger')
    else:
        db.session.delete(cat)
        db.session.commit()
        flash('Категория удалена.', 'success')
    return redirect(url_for('admin.categories'))


# ─────────────────────────── Employees ───────────────────────────

@bp.route('/employees')
@login_required
@admin_required
def employees():
    employees_list = Employee.query.join(User).order_by(User.last_name).all()
    return render_template('admin/employees/index.html', title='Сотрудники', employees=employees_list)


@bp.route('/employees/new', methods=['GET', 'POST'])
@login_required
@admin_required
def employee_new():
    form = EmployeeForm()
    form.services.choices = [(s.id, s.name) for s in Service.query.filter_by(is_active=True).all()]
    if form.validate_on_submit():
        # Create user
        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role='employee'
        )
        if form.password.data:
            user.set_password(form.password.data)
        else:
            user.set_password('employee123')
        db.session.add(user)
        db.session.flush()

        # Create employee profile
        employee = Employee(
            user_id=user.id,
            specialization=form.specialization.data,
            bio=form.bio.data,
            experience_years=form.experience_years.data or 0,
            is_available=form.is_available.data
        )
        if form.photo.data and form.photo.data.filename:
            filename = save_image(form.photo.data, 'employees')
            if filename:
                employee.photo = filename

        # Assign services
        selected_services = Service.query.filter(Service.id.in_(form.services.data or [])).all()
        employee.services = selected_services

        db.session.add(employee)
        db.session.commit()

        # Create default work schedule (Mon-Fri 9-18)
        for day in range(5):
            schedule = WorkSchedule(
                employee_id=employee.id,
                day_of_week=day,
                start_time=time(9, 0),
                end_time=time(18, 0),
                is_working=True
            )
            db.session.add(schedule)
        db.session.commit()

        flash('Сотрудник добавлен.', 'success')
        return redirect(url_for('admin.employee_detail', employee_id=employee.id))
    form.is_available.data = True
    return render_template('admin/employees/form.html', title='Новый сотрудник', form=form)


@bp.route('/employees/<int:employee_id>')
@login_required
@admin_required
def employee_detail(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    recent_bookings = (Booking.query
                       .filter_by(employee_id=employee_id)
                       .order_by(Booking.booking_date.desc())
                       .limit(10).all())
    return render_template('admin/employees/detail.html',
                           title=employee.user.full_name,
                           employee=employee,
                           recent_bookings=recent_bookings)


@bp.route('/employees/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def employee_edit(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = EmployeeForm(employee_id=employee_id)
    form.services.choices = [(s.id, s.name) for s in Service.query.filter_by(is_active=True).all()]

    if form.validate_on_submit():
        employee.user.first_name = form.first_name.data.strip()
        employee.user.last_name = form.last_name.data.strip()
        employee.user.email = form.email.data.lower().strip()
        employee.user.phone = form.phone.data.strip() if form.phone.data else None
        if form.password.data:
            employee.user.set_password(form.password.data)

        employee.specialization = form.specialization.data
        employee.bio = form.bio.data
        employee.experience_years = form.experience_years.data or 0
        employee.is_available = form.is_available.data

        if form.photo.data and form.photo.data.filename:
            filename = save_image(form.photo.data, 'employees')
            if filename:
                employee.photo = filename

        selected_services = Service.query.filter(Service.id.in_(form.services.data or [])).all()
        employee.services = selected_services

        db.session.commit()
        flash('Данные сотрудника обновлены.', 'success')
        return redirect(url_for('admin.employee_detail', employee_id=employee.id))

    # Pre-fill form
    form.first_name.data = employee.user.first_name
    form.last_name.data = employee.user.last_name
    form.email.data = employee.user.email
    form.phone.data = employee.user.phone
    form.specialization.data = employee.specialization
    form.bio.data = employee.bio
    form.experience_years.data = employee.experience_years
    form.is_available.data = employee.is_available
    form.services.data = [s.id for s in employee.services]

    return render_template('admin/employees/form.html',
                           title='Редактировать сотрудника',
                           form=form, employee=employee)


@bp.route('/employees/<int:employee_id>/schedule', methods=['GET', 'POST'])
@login_required
@admin_required
def employee_schedule(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    form = WorkScheduleForm()

    day_fields = [
        (0, 'mon'), (1, 'tue'), (2, 'wed'), (3, 'thu'),
        (4, 'fri'), (5, 'sat'), (6, 'sun')
    ]

    if form.validate_on_submit():
        # Delete existing
        WorkSchedule.query.filter_by(employee_id=employee_id).delete()
        for day_num, prefix in day_fields:
            working = getattr(form, f'{prefix}_working').data
            start = getattr(form, f'{prefix}_start').data
            end = getattr(form, f'{prefix}_end').data
            if working and start and end:
                sched = WorkSchedule(
                    employee_id=employee_id,
                    day_of_week=day_num,
                    start_time=start,
                    end_time=end,
                    is_working=True
                )
                db.session.add(sched)
            else:
                sched = WorkSchedule(
                    employee_id=employee_id,
                    day_of_week=day_num,
                    start_time=time(9, 0),
                    end_time=time(18, 0),
                    is_working=False
                )
                db.session.add(sched)
        db.session.commit()
        flash('Расписание сохранено.', 'success')
        return redirect(url_for('admin.employee_detail', employee_id=employee_id))

    # Pre-fill from existing schedule
    existing = {s.day_of_week: s for s in employee.schedules}
    for day_num, prefix in day_fields:
        sched = existing.get(day_num)
        if sched:
            getattr(form, f'{prefix}_working').data = sched.is_working
            getattr(form, f'{prefix}_start').data = sched.start_time
            getattr(form, f'{prefix}_end').data = sched.end_time
        else:
            getattr(form, f'{prefix}_start').data = time(9, 0)
            getattr(form, f'{prefix}_end').data = time(18, 0)

    return render_template('admin/employees/schedule.html',
                           title='Расписание',
                           employee=employee, form=form)


@bp.route('/employees/<int:employee_id>/delete', methods=['POST'])
@login_required
@admin_required
def employee_delete(employee_id):
    employee = Employee.query.get_or_404(employee_id)
    if employee.bookings:
        employee.is_available = False
        employee.user.is_active = False
        db.session.commit()
        flash('Сотрудник деактивирован (есть записи).', 'warning')
    else:
        user = employee.user
        db.session.delete(employee)
        db.session.delete(user)
        db.session.commit()
        flash('Сотрудник удалён.', 'success')
    return redirect(url_for('admin.employees'))


# ─────────────────────────── Clients ───────────────────────────

@bp.route('/clients')
@login_required
@admin_required
def clients():
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '')
    query = User.query.filter_by(role='client')
    if search:
        query = query.filter(
            (User.first_name + ' ' + User.last_name).ilike(f'%{search}%')
            | User.email.ilike(f'%{search}%')
            | User.phone.ilike(f'%{search}%')
        )
    clients_list = query.order_by(User.created_at.desc()).paginate(page=page, per_page=25, error_out=False)
    return render_template('admin/clients/index.html', title='Клиенты',
                           clients=clients_list, search=search)


@bp.route('/clients/<int:client_id>')
@login_required
@admin_required
def client_detail(client_id):
    client = User.query.filter_by(id=client_id, role='client').first_or_404()
    bookings = (Booking.query.filter_by(client_id=client_id)
                .order_by(Booking.booking_date.desc()).all())
    return render_template('admin/clients/detail.html',
                           title=client.full_name, client=client, bookings=bookings)


@bp.route('/clients/<int:client_id>/toggle', methods=['POST'])
@login_required
@admin_required
def client_toggle(client_id):
    client = User.query.filter_by(id=client_id, role='client').first_or_404()
    client.is_active = not client.is_active
    db.session.commit()
    status = 'активирован' if client.is_active else 'заблокирован'
    flash(f'Клиент {status}.', 'success')
    return redirect(url_for('admin.client_detail', client_id=client_id))


# ─────────────────────────── Reviews ───────────────────────────

@bp.route('/reviews')
@login_required
@admin_required
def reviews():
    page = request.args.get('page', 1, type=int)
    published = request.args.get('published', '')
    query = Review.query
    if published == '1':
        query = query.filter_by(is_published=True)
    elif published == '0':
        query = query.filter_by(is_published=False)
    reviews_list = query.order_by(Review.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/reviews/index.html', title='Отзывы',
                           reviews=reviews_list, current_filter=published)


@bp.route('/reviews/<int:review_id>/toggle', methods=['POST'])
@login_required
@admin_required
def review_toggle(review_id):
    review = Review.query.get_or_404(review_id)
    review.is_published = not review.is_published
    db.session.commit()
    status = 'опубликован' if review.is_published else 'скрыт'
    flash(f'Отзыв {status}.', 'success')
    return redirect(url_for('admin.reviews'))


@bp.route('/reviews/<int:review_id>/delete', methods=['POST'])
@login_required
@admin_required
def review_delete(review_id):
    review = Review.query.get_or_404(review_id)
    db.session.delete(review)
    db.session.commit()
    flash('Отзыв удалён.', 'success')
    return redirect(url_for('admin.reviews'))
