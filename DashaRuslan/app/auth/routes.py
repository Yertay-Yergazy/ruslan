from urllib.parse import urljoin, urlsplit
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.auth import bp
from app.auth.forms import LoginForm, RegisterForm, ProfileForm, ChangePasswordForm
from app.models import db, User
from app.utils import save_image


def is_safe_url(target):
    if not target:
        return False
    ref_url = urlsplit(request.host_url)
    test_url = urlsplit(urljoin(request.host_url, target))
    return test_url.scheme in ('http', 'https') and ref_url.netloc == test_url.netloc


@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('client.index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower().strip()).first()
        if user and user.check_password(form.password.data):
            if not user.is_active:
                flash('Ваш аккаунт заблокирован. Обратитесь к администратору.', 'danger')
                return redirect(url_for('auth.login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not is_safe_url(next_page):
                next_page = None
            if user.is_admin():
                return redirect(next_page or url_for('admin.dashboard'))
            return redirect(next_page or url_for('client.index'))
        flash('Неверный email или пароль.', 'danger')
    return render_template('auth/login.html', title='Вход', form=form)


@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('client.index'))
    form = RegisterForm()
    if form.validate_on_submit():
        user = User(
            first_name=form.first_name.data.strip(),
            last_name=form.last_name.data.strip(),
            email=form.email.data.lower().strip(),
            phone=form.phone.data.strip() if form.phone.data else None,
            role='client'
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация прошла успешно! Добро пожаловать!', 'success')
        login_user(user)
        return redirect(url_for('client.index'))
    return render_template('auth/register.html', title='Регистрация', form=form)


@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы.', 'info')
    return redirect(url_for('client.index'))


@bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    form = ProfileForm(obj=current_user)
    pwd_form = ChangePasswordForm()

    if form.validate_on_submit() and 'save_profile' in request.form:
        current_user.first_name = form.first_name.data.strip()
        current_user.last_name = form.last_name.data.strip()
        current_user.phone = form.phone.data.strip() if form.phone.data else None

        # Handle avatar upload
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = save_image(file, 'avatars')
                if filename:
                    current_user.avatar = filename

        db.session.commit()
        flash('Профиль обновлён.', 'success')
        return redirect(url_for('auth.profile'))

    if pwd_form.validate_on_submit() and 'change_password' in request.form:
        if current_user.check_password(pwd_form.old_password.data):
            current_user.set_password(pwd_form.new_password.data)
            db.session.commit()
            flash('Пароль успешно изменён.', 'success')
        else:
            flash('Неверный текущий пароль.', 'danger')
        return redirect(url_for('auth.profile'))

    return render_template('auth/profile.html', title='Мой профиль',
                           form=form, pwd_form=pwd_form)
