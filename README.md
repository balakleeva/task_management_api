# Task Management API — руководство для QA

Документ для стажёров QA: как подключиться к API, с какими учётными данными работать и как проверять обычные и админские сценарии.

**Базовый URL (локальный стенд):**

```
http://localhost:8000
```

**Интерактивная документация (Swagger):** [http://localhost:8000/docs](http://localhost:8000/docs)

**Префикс API:** `/api/v1`

---

## Содержание

- [Запуск стенда](#запуск-стенда)
- [Учётные данные](#учётные-данные)
- [Авторизация](#авторизация)
- [Обычный пользователь и администратор](#обычный-пользователь-и-администратор)
- [Работа с админским API](#работа-с-админским-api)
- [Справочник эндпоинтов](#справочник-эндпоинтов)
- [Коды ответов и ошибки](#коды-ответов-и-ошибки)
- [Идеи для тест-кейсов](#идеи-для-тест-кейсов)

---

## Запуск стенда

Стенд поднимается через Docker (нужны Docker и Docker Compose).

```bash
cp .env.example .env
docker compose up --build -d
```

Проверка, что API отвечает:

```bash
curl http://localhost:8000/health
```

Ожидается JSON со статусом сервиса и подключением к БД.

Остановка:

```bash
docker compose down        # данные в БД сохраняются
docker compose down -v     # полный сброс БД (чистый стенд)
```

После `down -v` при следующем `up` снова создаётся дефолтный админ (см. ниже).

---

## Учётные данные

### Администратор (создаётся автоматически при старте API)

При первом запуске (и при пустой БД) API создаёт учётную запись админа. Параметры задаются в `.env`:

| Поле   | Переменная в `.env`      | Значение по умолчанию в `.env.example` |
| ------ | ------------------------ | -------------------------------------- |
| Email  | `DEFAULT_ADMIN_EMAIL`    | `admin@example.com`                    |
| Логин  | `DEFAULT_ADMIN_USERNAME` | `admin`                                |
| Пароль | `DEFAULT_ADMIN_PASSWORD` | `AdminCoolPassword123!`                    |

**Важно:** для входа используйте пароль из **вашего** файла `.env` (`DEFAULT_ADMIN_PASSWORD`), а не из примеров в интернете. Если логин возвращает `401 Incorrect username or password` — откройте `.env` и возьмите актуальный пароль.

В режиме `ENVIRONMENT=development` при каждом перезапуске контейнера пароль админа **синхронизируется** с `DEFAULT_ADMIN_PASSWORD` из `.env` (удобно после смены пароля в конфиге).

Проверить, что админ есть в БД:

```bash
docker compose exec db psql -U task_admin -d task_management_dev -c \
  "SELECT email, username, is_admin FROM users WHERE is_admin = true;"
```

### Обычный пользователь

Свободного «тестового» пользователя по умолчанию нет — его нужно **зарегистрировать** через `POST /api/v1/auth/register` или создать в Swagger (`/docs` → Authentication → register).

Рекомендуемый шаблон для практики:

| Поле     | Пример                |
| -------- | --------------------- |
| email    | `qa.user@example.com` |
| username | `qauser`              |
| password | `QaTestPass123!`      |

Сохраняйте логин/пароль — они понадобятся для сценариев «только свои задачи».

---

## Авторизация

Большинство эндпоинтов требуют заголовок:

```
Authorization: Bearer <access_token>
```

### Вход администратора

```bash
curl -X POST "http://localhost:8000/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"username":"admin","password":"ВАШ_ПАРОЛЬ_ИЗ_.env"}'
```

В ответе: `access_token`, `refresh_token`, `token_type: bearer`.

### Проверка профиля и роли

```bash
curl -X GET "http://localhost:8000/api/v1/auth/me" \
  -H "Authorization: Bearer <access_token>"
```

У админа в ответе есть `"is_admin": true`. У обычного пользователя на `/auth/me` и `/users/me` — `"is_admin": false`.

Публичный профиль `GET /api/v1/users/{user_id}` **не** возвращает `is_admin` (намеренно).

### Swagger UI

1. Откройте [http://localhost:8000/docs](http://localhost:8000/docs)
2. `POST /api/v1/auth/login` → Execute → скопируйте `access_token`
3. Кнопка **Authorize** → вставьте токен (можно без слова `Bearer`, Swagger добавит сам)

---

## Обычный пользователь и администратор

|                       | Обычный пользователь | Администратор                      |
| --------------------- | -------------------- | ---------------------------------- |
| Префикс задач         | `/api/v1/tasks`      | `/api/v1/admin/tasks`              |
| Видимость задач       | Только свои          | Все пользователи                   |
| Создание задачи       | Только себе          | Себе или любому (`user_id` в теле) |
| Чужая задача по ID    | `404 Task not found` | `200` и данные задачи              |
| Доступ без `is_admin` | —                    | `403 Admin access required`        |

Задачи **изолированы по владельцу**: один пользователь не должен читать/менять задачи другого через `/api/v1/tasks`.

---

## Работа с админским API

**Базовый путь:** `/api/v1/admin/tasks`

**Требования:** валидный JWT + `is_admin: true`. Выдать права админа через API нельзя — только учётка из seed или ручное изменение БД (для QA обычно не нужно).

### Быстрый сценарий

1. Залогиниться как `admin` → сохранить `ADMIN_TOKEN`
2. Зарегистрировать `qauser` → создать задачу от его имени
3. Список всех задач админом:

```bash
curl -X GET "http://localhost:8000/api/v1/admin/tasks/" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

В каждом элементе списка есть объект `owner` (`id`, `email`, `username`) — удобно проверять владельца.

4. Фильтр по владельцу (нужен `user_id` из register/me):

```bash
curl -X GET "http://localhost:8000/api/v1/admin/tasks/?user_id=<UUID_пользователя>" \
  -H "Authorization: Bearer ADMIN_TOKEN"
```

5. Создать задачу **от имени другого пользователя**:

```bash
curl -X POST "http://localhost:8000/api/v1/admin/tasks/" \
  -H "Authorization: Bearer ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Задача от админа",
    "user_id": "<UUID_пользователя>",
    "priority": "HIGH"
  }'
```

6. Негатив: тот же запрос с токеном обычного пользователя → `403`

### Отличия ответа админа

- `AdminTaskResponse` = поля задачи + `owner`
- `POST /admin/tasks/` — в теле обязателен `user_id` (UUID владельца)
- Фильтры GET `/` те же, что у `/tasks/`, плюс query-параметр `user_id`

### Частые ошибки при тестировании админа

| Ситуация                         | Ожидаемый код                     |
| -------------------------------- | --------------------------------- |
| Нет заголовка Authorization      | `403` (HTTPBearer)                |
| Токен обычного пользователя      | `403` + `"Admin access required"` |
| Несуществующий `task_id`         | `404`                             |
| `user_id` при создании не найден | `404` User not found              |
| Неверный пароль при login        | `401`                             |

---

## Справочник эндпоинтов

### Authentication — `/api/v1/auth`

| Method | Endpoint                  | Auth | Описание                                       |
| ------ | ------------------------- | ---- | ---------------------------------------------- |
| POST   | `/register`               | —    | Регистрация                                    |
| POST   | `/login`                  | —    | Вход (username или email в поле `username`)    |
| POST   | `/refresh`                | —    | Обновление access token                        |
| GET    | `/me`                     | ✅   | Текущий пользователь (`is_admin` только здесь) |
| POST   | `/logout`                 | ✅   | Выход (клиент удаляет токен)                   |
| POST   | `/password-reset/request` | —    | Запрос сброса пароля                           |
| POST   | `/password-reset/confirm` | —    | Подтверждение сброса                           |
| POST   | `/verify-email`           | —    | Подтверждение email                            |
| POST   | `/resend-verification`    | —    | Повторная отправка письма                      |

### Users — `/api/v1/users`

| Method | Endpoint       | Auth | Описание                       |
| ------ | -------------- | ---- | ------------------------------ |
| GET    | `/me`          | ✅   | Свой профиль                   |
| PUT    | `/me`          | ✅   | Обновить профиль               |
| PUT    | `/me/password` | ✅   | Сменить пароль                 |
| DELETE | `/me`          | ✅   | Удалить аккаунт                |
| GET    | `/{user_id}`   | ✅   | Публичный профиль пользователя |

### Tasks — `/api/v1/tasks` (только свои задачи)

| Method | Endpoint              | Auth | Описание                        |
| ------ | --------------------- | ---- | ------------------------------- |
| POST   | `/`                   | ✅   | Создать задачу                  |
| GET    | `/`                   | ✅   | Список с фильтрами и пагинацией |
| GET    | `/{task_id}`          | ✅   | Задача по ID                    |
| PUT    | `/{task_id}`          | ✅   | Обновить                        |
| DELETE | `/{task_id}`          | ✅   | Удалить                         |
| PATCH  | `/{task_id}/status`   | ✅   | Сменить статус                  |
| PATCH  | `/{task_id}/priority` | ✅   | Сменить приоритет               |
| GET    | `/overdue`            | ✅   | Просроченные                    |
| GET    | `/statistics`         | ✅   | Статистика                      |

**GET `/` — query-параметры:** `skip`, `limit` (max 100), `status`, `priority`, `category_id`, `search`, `due_date_from`, `due_date_to`

**Статусы:** `TODO`, `IN_PROGRESS`, `COMPLETED`, `ARCHIVED`  
**Приоритеты:** `LOW`, `MEDIUM`, `HIGH`, `URGENT`

### Categories — `/api/v1/categories`

| Method | Endpoint               | Auth | Описание                |
| ------ | ---------------------- | ---- | ----------------------- |
| POST   | `/`                    | ✅   | Создать категорию       |
| GET    | `/`                    | ✅   | Список категорий        |
| GET    | `/{category_id}`       | ✅   | Категория по ID         |
| PUT    | `/{category_id}`       | ✅   | Обновить                |
| DELETE | `/{category_id}`       | ✅   | Удалить                 |
| GET    | `/{category_id}/stats` | ✅   | Число задач в категории |

### Admin — `/api/v1/admin/tasks` (все задачи, только админ)

| Method | Endpoint              | Auth  | Описание                        |
| ------ | --------------------- | ----- | ------------------------------- |
| GET    | `/`                   | Admin | Все задачи (+ фильтр `user_id`) |
| GET    | `/{task_id}`          | Admin | Любая задача                    |
| POST   | `/`                   | Admin | Создать задачу для `user_id`    |
| PUT    | `/{task_id}`          | Admin | Обновить любую задачу           |
| DELETE | `/{task_id}`          | Admin | Удалить любую задачу            |
| PATCH  | `/{task_id}/status`   | Admin | Статус                          |
| PATCH  | `/{task_id}/priority` | Admin | Приоритет                       |

### Служебные

| Method | Endpoint         | Auth | Описание     |
| ------ | ---------------- | ---- | ------------ |
| GET    | `/health`        | —    | Health check |
| GET    | `/metrics`       | —    | Метрики      |
| POST   | `/metrics/reset` | —    | Сброс метрик |

---

## Коды ответов и ошибки

| Код   | Когда встречается                                               |
| ----- | --------------------------------------------------------------- |
| `200` | Успешное чтение/обновление                                      |
| `201` | Создание ресурса                                                |
| `204` | Успешное удаление без тела                                      |
| `400` | Ошибка валидации тела/query                                     |
| `401` | Неверный или отсутствующий токен; неверный логин/пароль         |
| `403` | Нет прав (не админ, неактивный пользователь, нет Bearer)        |
| `404` | Ресурс не найден или нет доступа (чужая задача у обычного user) |
| `409` | Конфликт (email/username уже занят)                             |
| `422` | Ошибка схемы Pydantic                                           |

Типичное тело ошибки:

```json
{
  "detail": "Описание ошибки"
}
```

---

## Полезные ссылки

- Swagger UI: [http://localhost:8000/docs](http://localhost:8000/docs)
- ReDoc: [http://localhost:8000/redoc](http://localhost:8000/redoc)

При вопросах по стенду обращайтесь к наставнику: актуальный пароль админа всегда в `.env` → `DEFAULT_ADMIN_PASSWORD`.
