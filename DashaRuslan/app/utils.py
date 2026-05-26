import os
import uuid
from datetime import datetime, time, timedelta
from functools import wraps
from flask import current_app, abort
from flask_login import current_user
from werkzeug.utils import secure_filename


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin():
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def employee_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ('admin', 'employee'):
            abort(403)
        return f(*args, **kwargs)
    return decorated_function


def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']


def save_image(file, subfolder=''):
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"{uuid.uuid4().hex}.{ext}"
        upload_path = os.path.join(current_app.config['UPLOAD_FOLDER'], subfolder)
        os.makedirs(upload_path, exist_ok=True)
        file.save(os.path.join(upload_path, filename))
        return os.path.join(subfolder, filename).replace('\\', '/') if subfolder else filename
    return None


def generate_booking_number():
    now = datetime.utcnow()
    return f"AS{now.strftime('%Y%m%d')}{uuid.uuid4().hex[:6].upper()}"


def get_time_slots(start_hour, end_hour, slot_duration_minutes=30):
    """Generate list of time slots as time objects."""
    slots = []
    current = datetime.combine(datetime.today(), time(start_hour, 0))
    end = datetime.combine(datetime.today(), time(end_hour, 0))
    delta = timedelta(minutes=slot_duration_minutes)
    while current < end:
        slots.append(current.time())
        current += delta
    return slots


def get_busy_slots(employee_id, date, service_duration, exclude_booking_id=None):
    """Return set of start times that are busy for the employee on the date."""
    from app.models import Booking
    query = Booking.query.filter(
        Booking.employee_id == employee_id,
        Booking.booking_date == date,
        Booking.status.in_(['pending', 'confirmed', 'in_progress'])
    )
    if exclude_booking_id:
        query = query.filter(Booking.id != exclude_booking_id)
    bookings = query.all()

    busy = set()
    for booking in bookings:
        # Mark all slots covered by this booking
        slot_start = datetime.combine(date, booking.start_time)
        slot_end = datetime.combine(date, booking.end_time)
        cursor = slot_start
        while cursor < slot_end:
            busy.add(cursor.time())
            cursor += timedelta(minutes=30)
    return busy


def is_slot_available(employee_id, date, start_time_obj, service_duration):
    """Check if a time slot is available for a service."""
    from app.models import Booking, WorkSchedule
    if date == datetime.today().date() and datetime.combine(date, start_time_obj) <= datetime.now():
        return False

    # Check work schedule
    schedule = WorkSchedule.query.filter_by(
        employee_id=employee_id,
        day_of_week=date.weekday(),
        is_working=True
    ).first()
    if not schedule:
        return False

    end_time_obj = (datetime.combine(date, start_time_obj) +
                    timedelta(minutes=service_duration)).time()

    if start_time_obj < schedule.start_time or end_time_obj > schedule.end_time:
        return False

    # Check conflicts
    busy = get_busy_slots(employee_id, date, service_duration)

    # Verify none of the slots needed for our service are busy
    cursor = datetime.combine(date, start_time_obj)
    service_end = datetime.combine(date, end_time_obj)
    while cursor < service_end:
        if cursor.time() in busy:
            return False
        cursor += timedelta(minutes=30)
    return True


def format_time(t):
    """Format time object to HH:MM string."""
    if isinstance(t, time):
        return t.strftime('%H:%M')
    return str(t)


def stars_range(n):
    """Return range for star rating display."""
    return range(1, 6)
