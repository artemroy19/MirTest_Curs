# MirTest

MirTest - учебная платформа для полного цикла тестирования: преподаватель создаёт группы, наполняет банк вопросов, собирает тесты, назначает их студентам и проверяет развёрнутые ответы; студент вступает в группы, проходит назначенные тесты и смотрит доступные результаты.

Проект разделён на Django REST API и React SPA. Backend хранит пользователей, роли, группы, вопросы, тесты, назначения, попытки и результаты. Frontend предоставляет отдельные интерфейсы для студента и преподавателя, работает с API через JWT и показывает состояния прохождения, проверки и результатов. Для контейнерного запуска подготовлен Docker Compose: PostgreSQL, Django backend на Gunicorn и frontend-контейнер с nginx.

## Возможности

- регистрация и вход по email с JWT;
- профиль пользователя, смена пароля, загрузка аватара;
- роли пользователей: студент, преподаватель, администратор;
- группы студентов с кодами приглашения;
- банк вопросов преподавателя с категориями;
- типы вопросов: одиночный выбор, множественный выбор, краткий ответ, развёрнутый вопрос;
- конструктор тестов с выбором вопросов из банка и сортировкой;
- назначение тестов группам и отдельным студентам;
- лимит попыток, дедлайн, таймер;
- прохождение тестов с сохранением ответов;
- автоматический подсчёт баллов для закрытых и кратких вопросов;
- очередь ручной проверки развёрнутых вопросов;
- результаты и статистика для преподавателя;
- история результатов для студента;
- автоматические backend-тесты и фаззинг-тестирование входных JSON-данных.

## Стек

Backend:

- Python 3.11+
- Django 5.2
- Django REST Framework
- Simple JWT
- SQLite для локальной разработки
- PostgreSQL через `DATABASE_URL` для production
- Pillow для аватаров пользователей
- Gunicorn для запуска Django в Docker/production
- Hypothesis для фаззинг-тестирования backend

Frontend:

- React 18
- TypeScript
- Vite
- Axios
- Zustand
- React Router
- CSS Modules и общие CSS-стили
- `@dnd-kit` для drag-and-drop сортировки вопросов в конструкторе

Инфраструктура:

- Docker и Docker Compose
- PostgreSQL 16 в отдельном контейнере
- nginx во frontend-контейнере
- named volumes для PostgreSQL, аватаров пользователей и static
- Yandex Cloud VM как описанный сценарий облачного деплоя

## Структура проекта

```text
MirTest_curs/
  backend/                 Django API
    apps/
      accounts/            пользователи, авторизация, профиль
      groups/              группы и участники
      questions/           банк вопросов и категории
      tests/               тесты, вопросы тестов, назначения
      attempts/            попытки, ответы, проверка, результаты
      common/              общие модели и middleware
    mirtest/               settings, urls, wsgi
    manage.py
    requirements.txt
  frontend/                React SPA
    src/
      api/                 Axios-клиент
      app/                 маршрутизация
      components/          общие и доменные компоненты
      constants/           константы UI
      layout/              общий layout приложения
      pages/               страницы по ролям
      store/               Zustand session store
      styles/              глобальные стили
      types/               общие TS-типы
      utils/               утилиты
  readme.md
```

## Быстрый запуск

### Docker

Docker-запуск поднимает PostgreSQL, Django backend и nginx frontend.

```bash
docker compose up --build
```

### Backend

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Backend будет доступен на `http://127.0.0.1:8000/`.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Frontend будет доступен на `http://localhost:5173/`.

## Тестирование

Backend-тесты запускаются стандартным Django test runner:

```bash
cd backend
source venv/bin/activate
python manage.py test
```

Текущий набор включает обычные API-тесты и fuzz-тесты на Hypothesis:

- `backend/apps/accounts/tests.py`
- `backend/apps/accounts/test_fuzz.py`
- `backend/apps/groups/tests.py`
- `backend/apps/questions/tests.py`
- `backend/apps/questions/test_fuzz.py`
- `backend/apps/tests/tests.py`
- `backend/apps/attempts/tests.py`
- `backend/apps/attempts/test_fuzz.py`

Последний проверочный запуск: `62 tests OK`.

## CI

В проекте настроен GitHub Actions workflow:

```text
.github/workflows/ci.yml
```

CI запускается при `push` и `pull request` в ветку `main`.

Проверки:

- `backend-tests` - поднимает PostgreSQL 16 как service container, устанавливает Python 3.11 и зависимости из `backend/requirements.txt`, затем запускает `python manage.py test`. В этот набор входят обычные API-тесты и fuzz-тесты на Hypothesis.
- `frontend-build` - устанавливает Node.js 20, выполняет `npm ci` и `npm run build` в папке `frontend`.
- `docker-build` - запускается только после успешных backend/frontend проверок и выполняет `docker compose build`.

## Переменные окружения

Backend использует `backend/.env`:

- `SECRET_KEY` - секретный ключ Django;
- `DEBUG` - режим отладки;
- `ALLOWED_HOSTS` - список разрешённых host через запятую;
- `DATABASE_URL` - строка подключения, например `sqlite:///db.sqlite3` или PostgreSQL URL;
- `CORS_ALLOWED_ORIGINS` - разрешённые frontend-origin;
- `JWT_ACCESS_TOKEN_LIFETIME_MINUTES` - срок жизни access token;
- `JWT_REFRESH_TOKEN_LIFETIME_DAYS` - срок жизни refresh token.

Frontend использует `frontend/.env`:

- `VITE_API_URL` - базовый URL API, по умолчанию `http://localhost:8000/api`;

MirTest Created by Roytman Artem.
