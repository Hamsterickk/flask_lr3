from app import app, login_manager
from flask import render_template, request, redirect, url_for, session, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_wtf import FlaskForm
from flask_wtf.csrf import CSRFProtect
from wtforms import StringField, PasswordField, FloatField, TextAreaField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Email, Length, NumberRange, Optional, Regexp
import pickle
import os
import re
from datetime import datetime, timedelta
from app.models import User, Wallet

# Проверяем наличие email-validator
try:
    import email_validator
    _email_validator = Email()
except ImportError:
    _email_validator = Regexp(r'^[^@]+@[^@]+\.[^@]+$', message='Введите корректный email')


DATA_FILE = 'hotel_data.pkl'


class HotelStorage:
    def __init__(self):
        self.users = []
        self.max_ids = {'user': 0}

    def save(self, filename):
        with open(filename, 'wb') as f:
            pickle.dump({'users': self.users, 'max_ids': self.max_ids}, f)

    def load(self, filename):
        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                data = pickle.load(f)
                self.users = data['users']
                self.max_ids = data['max_ids']


storage = HotelStorage()
storage.load(DATA_FILE)


@login_manager.user_loader
def load_user(user_id):
    return next((u for u in storage.users if str(u.id) == user_id), None)


# ========== FLASK-WTF ФОРМЫ ==========

class RegisterForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), _email_validator])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=4)])
    confirm_password = PasswordField('Подтверждение', validators=[DataRequired()])


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])


class EditProfileForm(FlaskForm):
    name = StringField('Имя', validators=[Optional(), Length(max=100)])
    email = StringField('Email', validators=[Optional(), _email_validator])
    new_password = PasswordField('Новый пароль', validators=[Optional(), Length(min=4)])
    next = HiddenField()


class ReviewForm(FlaskForm):
    review_text = TextAreaField('Отзыв', validators=[DataRequired(), Length(max=500)])
    review_rating = IntegerField('Оценка', validators=[DataRequired(), NumberRange(min=1, max=5)])


class WalletTopupForm(FlaskForm):
    amount = FloatField('Сумма', validators=[DataRequired(), NumberRange(min=100, max=1000000)])
    card_number = StringField('Номер карты', validators=[DataRequired(), Length(min=16, max=19)])
    expiry = StringField('Срок', validators=[DataRequired(), Length(min=5, max=5)])
    cvc = StringField('CVC', validators=[DataRequired(), Length(min=3, max=3)])
    save_card = StringField('Сохранить', validators=[Optional()])


class BookingForm(FlaskForm):
    room_type = StringField('Тип номера', validators=[DataRequired()])
    first_name = StringField('Имя', validators=[DataRequired()])
    last_name = StringField('Фамилия', validators=[DataRequired()])
    phone = StringField('Телефон', validators=[DataRequired()])
    email = StringField('Email', validators=[Optional()])
    check_in = StringField('Заезд', validators=[DataRequired()])
    check_out = StringField('Выезд', validators=[DataRequired()])
    agree_privacy = StringField('Согласие', validators=[Optional()])


# ========== СТРАНИЦЫ (GET) ==========

@app.route('/')
@app.route('/index')
def index():
    form = LoginForm()
    register_form = RegisterForm()
    return render_template('index.html', form=form, register_form=register_form)


@app.route('/rooms')
def rooms():
    return render_template('rooms.html')


@app.route('/profile', methods=['GET'])
@login_required
def profile():
    form = EditProfileForm(obj=current_user)
    return render_template('profile.html', form=form)


@app.route('/booking')
def booking():
    room_type = request.args.get('type', 'standard')
    prices = {
        'standard': {'price': 4000, 'name': 'Стандарт двухместный',
                     'image': '3b824458b6be5ba54a0b4a8f91bee543b7e8845e.png'},
        'business': {'price': 8000, 'name': 'Бизнес двухместный',
                     'image': 'a8835fef9bd5262e7c5d4eb4a126f56258f4cce7.png'},
        'luxury': {'price': 12000, 'name': 'Люкс пентхаус двухместный',
                   'image': '31b3b7594a12c640a341a671b5342d65d87ad6dc.png'}
    }
    room = prices.get(room_type, prices['standard'])
    form = BookingForm()
    return render_template('booking.html', room=room, form=form)


@app.route('/restaurant')
def restaurant():
    return render_template('restaurant.html')


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/reviews')
def reviews():
    form = ReviewForm()
    return render_template('reviews.html', form=form)


@app.route('/service')
def service():
    return render_template('service.html')


@app.route('/spa')
def spa():
    return render_template('spa.html')


@app.route('/wallet', methods=['GET'])
@login_required
def wallet():
    form = WalletTopupForm()
    return render_template('wallet.html', form=form)


# ========== АВТОРИЗАЦИЯ ==========

@app.route('/register', methods=['POST'])
def register():
    form = RegisterForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            flash(errors[0])
        return redirect(url_for('index'))

    email = form.email.data
    password = form.password.data
    confirm = form.confirm_password.data

    if password != confirm:
        flash('Пароли не совпадают')
        return redirect(url_for('index'))

    if any(u.email == email for u in storage.users):
        flash('Email уже занят')
        return redirect(url_for('index'))

    name = email.split('@')[0] if '@' in email else 'Гость'

    user = User(storage.max_ids['user'] + 1)
    user.name = name
    user.email = email
    user.password = password
    user.create_wallet()
    storage.users.append(user)
    storage.max_ids['user'] += 1
    storage.save(DATA_FILE)
    login_user(user)
    flash('Регистрация успешна!', 'success')
    return redirect(url_for('profile'))


@app.route('/login', methods=['POST'])
def login():
    form = LoginForm()
    if not form.validate_on_submit():
        flash('Заполните все поля')
        return redirect(url_for('index'))

    email = form.email.data
    password = form.password.data
    user = next((u for u in storage.users if u.email == email and u.password == password), None)

    if user:
        login_user(user)
        flash('Вход выполнен успешно!', 'success')
        return redirect(url_for('profile'))
    else:
        flash('Неверный email или пароль')
        return redirect(url_for('index'))


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


# ========== ПРОФИЛЬ (PUT, PATCH) ==========

@app.route('/profile/edit', methods=['POST', 'PUT', 'PATCH'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            for error in errors:
                flash(error)
        return redirect(url_for('profile'))

    new_name = form.name.data.strip() if form.name.data else ''
    new_email = form.email.data.strip() if form.email.data else ''
    new_password = form.new_password.data.strip() if form.new_password.data else ''
    next_url = form.next.data or url_for('profile')

    if new_name:
        current_user.name = new_name
    if new_email:
        existing = next((u for u in storage.users if u.email == new_email and u.id != current_user.id), None)
        if existing:
            flash('Этот email уже используется')
        else:
            current_user.email = new_email
    if new_password:
        current_user.password = new_password
    storage.save(DATA_FILE)
    flash('Профиль обновлён', 'success')
    return redirect(next_url)


# ========== БРОНИРОВАНИЕ (POST, DELETE) ==========

@app.route('/booking/create', methods=['POST'])
@login_required
def create_booking():
    form = BookingForm()
    if not form.validate_on_submit():
        flash('Ошибка валидации формы')
        return redirect(request.referrer or url_for('booking'))

    room_type = form.room_type.data
    first_name = form.first_name.data
    last_name = form.last_name.data
    phone = form.phone.data
    check_in = form.check_in.data
    check_out = form.check_out.data
    agree_privacy = form.agree_privacy.data

    if not re.fullmatch(r'[а-яА-ЯёЁ]+', first_name):
        flash('Имя должно содержать только русские буквы')
        return redirect(request.referrer or url_for('booking'))

    if not re.fullmatch(r'[а-яА-ЯёЁ]+', last_name):
        flash('Фамилия должна содержать только русские буквы')
        return redirect(request.referrer or url_for('booking'))

    if len(re.sub(r'\D', '', phone)) != 11:
        flash('Введите корректный номер телефона')
        return redirect(request.referrer or url_for('booking'))

    if not agree_privacy:
        flash('Необходимо согласие на обработку персональных данных')
        return redirect(request.referrer or url_for('booking'))

    date_in = datetime.strptime(check_in, '%Y-%m-%d')
    date_out = datetime.strptime(check_out, '%Y-%m-%d')
    days = max((date_out - date_in).days, 1)

    prices = {'Стандарт двухместный': 4000, 'Бизнес двухместный': 8000, 'Люкс пентхаус двухместный': 12000}
    total_price = prices.get(room_type, 4000) * days

    if not current_user.wallet or current_user.wallet.balance < total_price:
        flash('Недостаточно средств. Пополните кошелёк.')
        return redirect(url_for('wallet'))

    current_user.wallet.balance -= total_price
    current_user.wallet.transactions.append({
        'date': datetime.now(),
        'amount': -total_price,
        'description': f'Бронь: {room_type} ({days} дн.)'
    })

    storage.save(DATA_FILE)
    flash(f'Бронирование подтверждено! Списанo {total_price} руб. за {days} дн.', 'success')
    return redirect(url_for('profile'))


@app.route('/booking/delete', methods=['DELETE', 'POST'])
@login_required
def delete_booking():
    flash('Функция удаления брони в разработке')
    return redirect(url_for('profile'))


# ========== ОТЗЫВЫ (POST, PATCH, DELETE) ==========

@app.route('/review/save', methods=['POST'])
@login_required
def save_review():
    form = ReviewForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            flash(errors[0])
        return redirect(url_for('reviews'))

    current_user.review_text = form.review_text.data
    current_user.review_rating = form.review_rating.data
    current_user.review_sent = True
    storage.save(DATA_FILE)
    flash('Отзыв сохранён', 'success')
    return redirect(url_for('reviews'))


@app.route('/review/edit', methods=['PUT', 'PATCH', 'POST'])
@login_required
def edit_review():
    form = ReviewForm()
    if not form.validate_on_submit():
        flash('Ошибка валидации')
        return redirect(url_for('reviews'))

    current_user.review_text = form.review_text.data
    current_user.review_rating = form.review_rating.data
    storage.save(DATA_FILE)
    return redirect(url_for('reviews'))


@app.route('/review/delete', methods=['DELETE', 'POST'])
@login_required
def delete_review():
    current_user.review_text = ""
    current_user.review_rating = 0
    current_user.review_sent = False
    storage.save(DATA_FILE)
    return '', 204


# ========== КОШЕЛЁК (POST) ==========

@app.route('/wallet/topup', methods=['POST'])
@login_required
def wallet_topup():
    form = WalletTopupForm()
    if not form.validate_on_submit():
        for field, errors in form.errors.items():
            flash(errors[0])
        return redirect(url_for('wallet'))

    amount = form.amount.data
    card_number = form.card_number.data.replace(' ', '')
    if len(card_number) != 16 or not card_number.isdigit():
        flash('Номер карты должен содержать 16 цифр')
        return redirect(url_for('wallet'))
    expiry = form.expiry.data
    cvc = form.cvc.data
    save_card = form.save_card.data

    try:
        exp_month, exp_year = expiry.split('/')
        exp_month = int(exp_month)
        exp_year = int('20' + exp_year)

        now = datetime.now()
        if exp_month == 12:
            last_day = datetime(exp_year + 1, 1, 1) - timedelta(days=1)
        else:
            last_day = datetime(exp_year, exp_month + 1, 1) - timedelta(days=1)

        if last_day < now:
            flash('Срок действия карты истёк')
            return redirect(url_for('wallet'))

        if not (1 <= exp_month <= 12):
            flash('Неверный месяц в сроке действия')
            return redirect(url_for('wallet'))
    except (ValueError, IndexError):
        flash('Неверный формат срока действия (ММ/ГГ)')
        return redirect(url_for('wallet'))

    if save_card != 'on':
        current_user.wallet.card_number = card_number
        current_user.wallet.expiry_date = expiry
        current_user.wallet.cvc = cvc
    else:
        current_user.wallet.card_number = ''
        current_user.wallet.expiry_date = ''
        current_user.wallet.cvc = ''

    current_user.wallet.balance += amount
    current_user.wallet.transactions.append({
        'date': datetime.now(),
        'amount': amount,
        'description': 'Пополнение кошелька'
    })

    storage.save(DATA_FILE)
    flash(f'Баланс пополнен на {amount:.2f} руб.', 'success')
    return redirect(url_for('wallet'))
