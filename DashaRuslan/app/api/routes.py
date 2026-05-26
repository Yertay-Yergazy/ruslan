from datetime import datetime, date, timedelta
from flask import jsonify, request
from flask_login import login_required
from app.api import bp
from app.models import Employee, Service, WorkSchedule, Booking
from app.utils import admin_required, get_busy_slots


@bp.route('/available-slots')
@login_required
def available_slots():
    """Return available time slots for a given employee, service and date."""
    employee_id = request.args.get('employee_id', type=int)
    service_id = request.args.get('service_id', type=int)
    date_str = request.args.get('date', '')

    if not all([employee_id, service_id, date_str]):
        return jsonify({'error': 'Missing parameters'}), 400

    try:
        target_date = datetime.strptime(date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    if target_date < date.today():
        return jsonify({'slots': []})

    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404

    employee = Employee.query.get(employee_id)
    if not employee or not employee.is_available:
        return jsonify({'error': 'Employee not found'}), 404

    if service not in employee.services:
        return jsonify({'slots': [], 'message': 'Этот мастер не выполняет выбранную услугу'})

    # Get employee work schedule for that day
    schedule = WorkSchedule.query.filter_by(
        employee_id=employee_id,
        day_of_week=target_date.weekday(),
        is_working=True
    ).first()

    if not schedule:
        return jsonify({'slots': [], 'message': 'Мастер не работает в этот день'})

    # Get all busy slots
    busy = get_busy_slots(employee_id, target_date, service.duration)

    # Generate all possible slots
    from datetime import time
    slots = []
    current = datetime.combine(target_date, schedule.start_time)
    schedule_end = datetime.combine(target_date, schedule.end_time)
    service_end_delta = timedelta(minutes=service.duration)

    slot_step = timedelta(minutes=30)

    while current + service_end_delta <= schedule_end:
        slot_time = current.time()
        if target_date == date.today() and current <= datetime.now():
            current += slot_step
            continue

        # Check if all slots needed for this service are free
        is_free = True
        check = current
        while check < current + service_end_delta:
            if check.time() in busy:
                is_free = False
                break
            check += slot_step

        if is_free:
            slots.append(slot_time.strftime('%H:%M'))
        current += slot_step

    return jsonify({'slots': slots})


@bp.route('/employees-for-service')
def employees_for_service():
    """Return employees who can perform a given service."""
    service_id = request.args.get('service_id', type=int)
    if not service_id:
        return jsonify({'error': 'Missing service_id'}), 400

    service = Service.query.get(service_id)
    if not service:
        return jsonify({'error': 'Service not found'}), 404

    employees = [
        {
            'id': e.id,
            'name': e.user.full_name,
            'specialization': e.specialization or 'Мастер',
            'experience': e.experience_years,
            'rating': e.avg_rating,
            'reviews': e.reviews_count
        }
        for e in service.employees if e.is_available
    ]
    return jsonify({'employees': employees})


@bp.route('/calendar-events')
@login_required
@admin_required
def calendar_events():
    """Return booking events for FullCalendar (admin use)."""
    start_str = request.args.get('start', '')
    end_str = request.args.get('end', '')
    employee_id = request.args.get('employee_id', type=int)

    try:
        start_dt = datetime.fromisoformat(start_str[:10]) if start_str else datetime.today()
        end_dt = datetime.fromisoformat(end_str[:10]) if end_str else start_dt + timedelta(days=30)
    except ValueError:
        return jsonify([])

    query = Booking.query.filter(
        Booking.booking_date >= start_dt.date(),
        Booking.booking_date <= end_dt.date(),
        Booking.status.in_(['pending', 'confirmed', 'in_progress'])
    )
    if employee_id:
        query = query.filter_by(employee_id=employee_id)

    color_map = {
        'pending': '#ffc107',
        'confirmed': '#0dcaf0',
        'in_progress': '#0d6efd',
        'completed': '#198754',
        'cancelled': '#dc3545'
    }

    events = []
    for b in query.all():
        start = datetime.combine(b.booking_date, b.start_time).isoformat()
        end = datetime.combine(b.booking_date, b.end_time).isoformat()
        events.append({
            'id': b.id,
            'title': f"{b.service.name} — {b.client.full_name}",
            'start': start,
            'end': end,
            'color': color_map.get(b.status, '#6c757d'),
            'url': f'/admin/bookings/{b.id}'
        })
    return jsonify(events)
