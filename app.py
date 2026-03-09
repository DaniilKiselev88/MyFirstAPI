from flask import Flask, request, jsonify
import json
import os
from marshmallow import Schema, fields, ValidationError
from flasgger import Swagger

app = Flask(__name__)
PORT = 5000

# Файл для сохранения данных
DATA_FILE = 'users.json'

def load_users():
    """Загрузка пользователей из файла"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_users(users):
    """Сохранение пользователей в файл"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

# Загрузка данных при старте
users = load_users()

# Настройка Swagger для документации API
swagger_config = {
    "headers": [],
    "specs": [
        {
            "endpoint": 'apispec',
            "route": '/apispec.json',
            "rule_filter": lambda rule: True,  # все endpoints
            "model_filter": lambda tag: True,  # все теги
        }
    ],
    "static_url_path": "/flasgger_static",
    "swagger_ui": True,
    "specs_route": "/docs/"
}
swagger = Swagger(app, config=swagger_config)

# Схема валидации для пользователей
class UserSchema(Schema):
    name = fields.Str(required=True, validate=lambda n: len(n) > 0, error_messages={
        "required": "Имя обязательно",
        "validator_failed": "Имя не может быть пустым"
    })
    email = fields.Email(required=True, error_messages={
        "required": "Email обязателен",
        "invalid": "Некорректный формат email"
    })

user_schema = UserSchema()

@app.route('/users', methods=['GET'])
def get_users():
    """
    Получить всех пользователей
    ---
    responses:
      200:
        description: Список пользователей
        schema:
          type: array
          items:
            type: object
            properties:
              id:
                type: integer
              name:
                type: string
              email:
                type: string
    """
    return jsonify(users)

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """
    Получить пользователя по ID
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
        description: ID пользователя
    responses:
      200:
        description: Пользователь найден
      404:
        description: Пользователь не найден
    """
    user = next((u for u in users if u['id'] == user_id), None)
    if user:
        return jsonify(user)
    else:
        return jsonify({'error': 'Пользователь не найден'}), 404

@app.route('/users', methods=['POST'])
def create_user():
    """
    Создание нового пользователя
    ---
    parameters:
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
              example: "Анна"
            email:
              type: string
              example: "anna@example.com"
    responses:
      201:
        description: Пользователь создан
      400:
        description: Неверные данные
      409:
        description: Email уже существует
    """
    try:
        data = user_schema.load(request.get_json())
    except ValidationError as err:
        return jsonify({'error': err.messages}), 400

    # Проверка на дублирование email
    if any(u['email'] == data['email'] for u in users):
        return jsonify({'error': 'Email уже существует'}), 409

    new_user = {
        'id': max([u['id'] for u in users], default=0) + 1,
        'name': data['name'],
        'email': data['email']
    }
    users.append(new_user)
    save_users(users)  # Сохранение в файл
    return jsonify(new_user), 201

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """
    Обновление пользователя
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
      - name: body
        in: body
        required: true
        schema:
          type: object
          properties:
            name:
              type: string
            email:
              type: string
    responses:
      200:
        description: Пользователь обновлён
      404:
        description: Пользователь не найден
      409:
        description: Email уже существует у другого пользователя
    """
    data = request.get_json()
    user = next((u for u in users if u['id'] == user_id), None)
    if not user:
        return jsonify({'error': 'Пользователь не найден'}), 404

    if 'name' in data:
        user['name'] = data['name']
    if 'email' in data:
        # Проверка на дублирование email (кроме текущего пользователя)
        if any(u['email'] == data['email'] and u['id'] != user_id for u in users):
            return jsonify({'error': 'Email уже существует'}), 409
        user['email'] = data['email']

    save_users(users)
    return jsonify(user)

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """
    Удаление пользователя
    ---
    parameters:
      - name: user_id
        in: path
        type: integer
        required: true
    responses:
      200:
        description: Пользователь удалён
      404:
        description: Пользователь не найден
    """
    global users
    user_index = next((i for i, u in enumerate(users) if u['id'] == user_id), None)
    if user_index is not None:
        users.pop(user_index)
        save_users(users)
        return jsonify({'message': 'Пользователь удалён'})
    else:
        return jsonify({'error': 'Пользователь не найден'}), 404

# Глобальная обработка ошибок
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Ресурс не найден'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Внутренняя ошибка сервера'}), 500


if __name__ == '__main__':
    app.run(port=PORT, debug=False)  # Убираем debug
