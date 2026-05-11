"""
Инициализация базы данных с тестовыми данными.
Запуск: python init_db.py
"""
from datetime import date, time, timedelta, datetime
from app import create_app
from app.models import (db, User, ServiceCategory, Service, Employee,
                         WorkSchedule, Booking, Review)
from app.utils import generate_booking_number
from slugify import slugify

app = create_app()


def init_db():
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("✅ Таблицы созданы")

        # ── Admin ──────────────────────────────
        admin = User(
            first_name='Асхат', last_name='Администратор',
            email='admin@autoservice.kz', role='admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        # ── Service Categories ─────────────────
        cats_data = [
            ('Техническое обслуживание', 'to', 'fa-oil-can', 0),
            ('Диагностика', 'diagnostika', 'fa-laptop-medical', 1),
            ('Кузовной ремонт', 'kuzov', 'fa-car-crash', 2),
            ('Шиномонтаж', 'shiny', 'fa-tire', 3),
            ('Электрика', 'elektrika', 'fa-bolt', 4),
            ('Подвеска и рулевое', 'podveska', 'fa-car', 5),
        ]
        categories = {}
        for name, slug, icon, order in cats_data:
            cat = ServiceCategory(name=name, slug=slug, icon=icon,
                                  sort_order=order, is_active=True)
            db.session.add(cat)
            categories[slug] = cat
        db.session.flush()

        # ── Services (цены в тенге) ────────────
        services_data = [
            ('Замена масла и фильтра', 'to', 12000, 30,
             'Замена моторного масла и масляного фильтра. Включает проверку основных систем автомобиля.', True),
            ('ТО-1 (15 000 км)', 'to', 25000, 90,
             'Плановое техническое обслуживание. Замена масла, фильтров, проверка тормозов и подвески.', True),
            ('ТО-2 (30 000 км)', 'to', 45000, 180,
             'Расширенное техническое обслуживание. Полная проверка и замена расходников.', True),
            ('Компьютерная диагностика', 'diagnostika', 8000, 45,
             'Полная компьютерная диагностика всех систем автомобиля.', True),
            ('Диагностика двигателя', 'diagnostika', 12000, 60,
             'Углублённая диагностика двигателя и топливной системы.', False),
            ('Ремонт вмятин без покраски', 'kuzov', 15000, 120,
             'Удаление небольших вмятин без покраски методом PDR.', True),
            ('Кузовной ремонт', 'kuzov', 40000, 480,
             'Ремонт и восстановление деталей кузова любой сложности.', False),
            ('Шиномонтаж (4 колеса)', 'shiny', 6000, 45,
             'Замена резины на дисках 4 колеса. Балансировка в комплекте.', True),
            ('Балансировка колёс', 'shiny', 4000, 30,
             'Балансировка 4 колёс для ровного движения.', False),
            ('Замена тормозных колодок', 'podveska', 14000, 60,
             'Замена передних или задних тормозных колодок с проверкой дисков.', True),
            ('Замена амортизаторов', 'podveska', 32000, 120,
             'Замена пары амортизаторов (передних или задних).', True),
            ('Замена аккумулятора', 'elektrika', 18000, 30,
             'Замена аккумулятора и проверка генератора.', False),
            ('Диагностика электрики', 'elektrika', 10000, 60,
             'Поиск и устранение неисправностей электрической системы.', False),
        ]
        services = []
        for name, cat_slug, price, duration, desc, featured in services_data:
            svc = Service(
                name=name,
                short_description=desc[:120] if desc else None,
                description=desc,
                price=price,
                duration=duration,
                category_id=categories[cat_slug].id,
                is_active=True,
                is_featured=featured
            )
            db.session.add(svc)
            services.append(svc)
        db.session.flush()

        # ── Employees (казахстанские имена) ────
        employees_data = [
            ('Нурлан', 'Ахметов', 'nurlan@autoservice.kz', '+7 (701) 111-22-33',
             'Слесарь-механик', 'Опытный механик с 10-летним стажем. Специализируется на ТО и ремонте двигателей.', 10,
             [0, 1, 2, 3]),
            ('Бауыржан', 'Сейтқали', 'baurzhan@autoservice.kz', '+7 (702) 222-33-44',
             'Диагност', 'Сертифицированный специалист по компьютерной диагностике автомобилей.', 7,
             [3, 4, 11, 12]),
            ('Дәурен', 'Жақсыбеков', 'dauren@autoservice.kz', '+7 (705) 333-44-55',
             'Мастер по кузову', 'Эксперт в области кузовного ремонта и покраски.', 12,
             [5, 6]),
            ('Серік', 'Оразов', 'serik@autoservice.kz', '+7 (707) 444-55-66',
             'Шиномонтажник / Слесарь', 'Мастер по шиномонтажу и ремонту подвески.', 5,
             [7, 8, 9, 10]),
        ]
        emps = []
        for fname, lname, email, phone, spec, bio, exp, svc_indices in employees_data:
            u = User(first_name=fname, last_name=lname, email=email, phone=phone, role='employee')
            u.set_password('employee123')
            db.session.add(u)
            db.session.flush()

            emp = Employee(user_id=u.id, specialization=spec, bio=bio,
                           experience_years=exp, is_available=True)
            emp.services = [services[i] for i in svc_indices]
            db.session.add(emp)
            db.session.flush()
            emps.append(emp)

            # Work schedule Mon-Fri 9-18, Sat 10-16
            for day in range(5):  # Mon–Fri
                db.session.add(WorkSchedule(
                    employee_id=emp.id, day_of_week=day,
                    start_time=time(9, 0), end_time=time(18, 0), is_working=True
                ))
            db.session.add(WorkSchedule(  # Saturday
                employee_id=emp.id, day_of_week=5,
                start_time=time(10, 0), end_time=time(16, 0), is_working=True
            ))
            db.session.add(WorkSchedule(  # Sunday - off
                employee_id=emp.id, day_of_week=6,
                start_time=time(9, 0), end_time=time(18, 0), is_working=False
            ))

        # ── Client users (казахстанские клиенты) ──
        clients = []
        clients_data = [
            ('Айгерим', 'Бекова', 'aigerim@mail.ru', '+7 (701) 555-11-22'),
            ('Ержан', 'Тәшенов', 'yerzhan@mail.ru', '+7 (702) 555-33-44'),
            ('Динара', 'Сәрсенова', 'dinara@mail.ru', '+7 (705) 555-55-66'),
            ('Арман', 'Жұмабеков', 'arman@mail.ru', '+7 (777) 555-77-88'),
        ]
        for fname, lname, email, phone in clients_data:
            u = User(first_name=fname, last_name=lname, email=email, phone=phone, role='client')
            u.set_password('client123')
            db.session.add(u)
            clients.append(u)
        db.session.flush()

        # ── Sample Bookings ────────────────────
        today = date.today()
        bookings_data = [
            (0, 0, 0, today + timedelta(days=1), time(10, 0), time(10, 30), 'confirmed', 'Toyota Camry 2020', ''),
            (1, 1, 1, today + timedelta(days=2), time(11, 0), time(11, 45), 'pending', 'Hyundai Tucson 2021', 'Горит чек-энгин'),
            (2, 2, 5, today - timedelta(days=3), time(9, 0), time(11, 0), 'completed', 'Kia Sportage 2022', ''),
            (3, 3, 7, today - timedelta(days=5), time(14, 0), time(14, 45), 'completed', 'Lada Vesta 2021', ''),
            (0, 0, 3, today - timedelta(days=7), time(10, 0), time(10, 45), 'completed', 'Toyota Camry 2020', ''),
        ]
        booking_objects = []
        for ci, ei, si, bd, st, et, status, car, notes in bookings_data:
            b = Booking(
                booking_number=generate_booking_number(),
                client_id=clients[ci].id,
                employee_id=emps[ei].id,
                service_id=services[si].id,
                booking_date=bd,
                start_time=st,
                end_time=et,
                status=status,
                total_price=services[si].price,
                car_info=car,
                notes=notes
            )
            db.session.add(b)
            booking_objects.append(b)
        db.session.flush()

        # ── Reviews ───────────────────────────
        reviews_data = [
            (2, 5, 'Өте жақсы сервис! Жылдам және сапалы жасалды. Ұсынамын!'),
            (3, 4, 'Жақсы шиномонтаж, сыпайы шеберлер. Нәтиже керемет.'),
            (4, 5, 'Компьютерлік диагностика жасырын мәселені анықтауға көмектесті. Рахмет!'),
        ]
        for bidx, rating, comment in reviews_data:
            r = Review(
                booking_id=booking_objects[bidx].id,
                client_id=booking_objects[bidx].client_id,
                rating=rating,
                comment=comment,
                is_published=True
            )
            db.session.add(r)

        db.session.commit()
        print("✅ База данных инициализирована с тестовыми данными!")
        print("\n📋 Учётные данные:")
        print("   Администратор: admin@autoservice.kz / admin123")
        print("   Клиент:       aigerim@mail.ru / client123")
        print("   Сотрудник:    nurlan@autoservice.kz / employee123")
        print("\n🌐 Запуск: PORT=8081 python run.py")
        print("   URL: http://127.0.0.1:8081")


if __name__ == '__main__':
    init_db()
