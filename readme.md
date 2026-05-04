# MirTest

MirTest - учебная платформа для создания, назначения, прохождения и проверки тестов. Проект разделён на Django REST API и React SPA, поддерживает роли `student`, `teacher`, `admin`, банк вопросов, группы, назначения, автоматическую проверку закрытых вопросов и ручную проверку развёрнутых вопросов.

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
- история результатов для студента.

## Стек

Backend:

- Python 3.11+
- Django 5.2
- Django REST Framework
- Simple JWT
- SQLite для локальной разработки
- PostgreSQL через `DATABASE_URL` для production
- Pillow для аватаров и медиа

Frontend:

- React 18
- TypeScript
- Vite
- Axios
- Zustand
- React Router
- CSS Modules и общие CSS-стили
- `@dnd-kit` для drag-and-drop в конструкторе тестов

## Структура проекта

```text
MirTest_curs/
  backend/                 Django API
    apps/
      accounts/            пользователи, auth, профиль
      groups/              группы и участники
      questions/           банк вопросов, категории, медиа
      tests/               тесты, вопросы тестов, назначения
      attempts/            попытки, ответы, проверка, scoring
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
  docs/                    подробная документация
  readme.md
```

## Быстрый запуск

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
