# myapi.py
from models import User, UserExpense
from database import db, app
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
from flask import Flask, request, jsonify
from database import app, db, jwt
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity
)


class Registation():
# Регистрация
    @app.route('/register', methods=['POST'])
    def register():
        data = request.get_json()
        if User.query.filter_by(username=data['username']).first():
            return jsonify({"msg": "Пользователь с таким именем уже существует"}), 400
        if User.query.filter_by(email=data['email']).first():
            return jsonify({"msg": "Email уже используется"}), 400

        user = User(username=data['username'], email=data.data['email'])
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        return jsonify({"msg": "Пользователь успешно зарегистрирован"}), 201

    # Авторизация
    @app.route('/login', methods=['POST'])
    def login():
        data = request.get_json()
        user = User.query.filter_by(username=data['username']).first()

        if user and user.check_password(data['password']):
            access_token = create_access_token(identity=user.username)
            return jsonify(access_token=access_token), 200

        return jsonify({"msg": "Неверное имя пользователя или пароль"}), 401

    # Защищённый маршрут
    @app.route('/protected', methods=['GET'])
    @jwt_required()
    def protected():
        current_user = get_jwt_identity()
        return jsonify(logged_in_as=current_user), 200
    



class MyAPI:
    def __init__(self, user_input=None, selected_category=None, note_id=None, user_id=None):
        self.user_input = user_input
        self.selected_category = selected_category
        self.note_id = note_id
        self.user_id = user_id

    def get_user_id(self):
        if not self.username:
            return None
        user = User.query.filter_by(username=self.username).first()
        return user.id if user else None

    def get_period(self, period_type="month", start_date=None, end_date=None):
        now = datetime.now()

        def parse_date(date_input):
            if isinstance(date_input, str):
                try:
                    return datetime.fromisoformat(date_input)
                except ValueError:
                    raise ValueError(f"Неверный формат даты: {date_input}. Используйте ISO формат.")
            elif isinstance(date_input, datetime):
                return date_input
            else:
                raise TypeError("start_date и end_date должны быть строкой или datetime")

        period_type = str(period_type).strip().lower()

        if period_type == "week":
            start = (now - timedelta(days=7)).replace(hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period_type == "month":
            prev_month = now - relativedelta(months=1)
            start = prev_month.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period_type == "3months":
            three_months_ago = now - relativedelta(months=3)
            start = three_months_ago.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = now
        elif period_type == "all_time":
            start = datetime(1970, 1, 1)
            end = now
        elif period_type == "custom":
            if not start_date or not end_date:
                raise ValueError("Для типа 'custom' необходимо указать start_date и end_date")
            start = parse_date(start_date)
            end = parse_date(end_date)
            if start > end:
                raise ValueError("start_date не может быть позже end_date")
        else:
            raise ValueError(f"Неизвестный тип периода: {period_type}")

        return start, end

    def get_note_id(self, user_input, selected_category, user_id):
        try:
            expense = UserExpense.query.filter_by(
                expense=user_input,
                category=selected_category,
                user_id=self.get_user_id()
            ).first()

            if expense:
                print(f"Найден ID: {expense.id}")
                return expense.id
            else:
                print("Запись не найдена.")
                return None
        except Exception as e:
            print(f"Ошибка при поиске ID: {e}")
            return None

    def add_expense(self, user_input, selected_category, user_id):
        try:
            new_expense = UserExpense(
                expense=user_input,
                category=selected_category,
                user_id=self.get_user_id()
            )
            db.session.add(new_expense)
            db.session.commit()
            print(f"Расход {user_input} добавлен")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при добавлении расхода: {e}")

    def update_expense(self, user_input, selected_category, note_id):
        try:
            expense = UserExpense.query.get(note_id)
            if not expense:
                print("Запись не найдена")
                return

            expense.expense = user_input
            expense.category = selected_category
            db.session.commit()
            print(f"Расход {note_id} обновлён")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при обновлении: {e}")

    def delete_expense(self, note_id):
        try:
            expense = UserExpense.query.get(note_id)
            if not expense:
                print("Запись не найдена")
                return
            if not expense:
                print(f"Расход с ID {note_id} не найден")
                return False

        # Проверяем, принадлежит ли запись текущему пользователю
            if expense.user_id != self.user_id:
                print(f"Ошибка: Расход {note_id} принадлежит другому пользователю")
                return False
        
            db.session.delete(expense)
            db.session.commit()
            print(f"Расход {note_id} удалён")
        except Exception as e:
            db.session.rollback()
            print(f"Ошибка при удалении: {e}")

    def get_column_values_in_period(self, period_type="month"):
        try:
            start_date, end_date = self.get_period(period_type)
            expenses = UserExpense.query.filter(
                UserExpense.created_at >= start_date,
                UserExpense.created_at < end_date
            ).all()

            return [float(exp.expense) for exp in expenses]
        except Exception as e:
            print(f"Ошибка при получении данных за период: {e}")
            return []

    def get_column_values_in_category(self, selected_category, period_type="month"):
        try:
            start_date, end_date = self.get_period(period_type)
            expenses = UserExpense.query.filter(
                UserExpense.created_at >= start_date,
                UserExpense.created_at < end_date,
                UserExpense.category == selected_category
            ).all()

            return [float(exp.expense) for exp in expenses]
        except Exception as e:
            print(f"Ошибка при получении данных по категории: {e}")
            return []

    def get_all_values(self, selected_category, period_type):
        try:
            all_expenses = self.get_column_values_in_period(period_type)
            category_expenses = self.get_column_values_in_category(selected_category, period_type)

            total_all = sum(all_expenses)
            total_category = sum(category_expenses)

            if total_category == 0:
                return 0.0

            percentage = (total_all / total_category) * 100
            return round(percentage, 2)
        except Exception as e:
            print(f"Ошибка при расчёте процентов: {e}")
            return 0.0

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
    
    