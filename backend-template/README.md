# backend-template

Стартовый шаблон бэкенда на FastAPI: async SQLAlchemy 2.0, Alembic-миграции,
модульная структура, фоновые задачи, Docker. Postgres из коробки через
`docker compose up`, SQLite как самый быстрый путь для локальных
экспериментов без Docker. `database.py` и общий подход — по образцу
настоящего бэкенда с изменениями под стартовый шаблон.

## Структура

```
.
├── master.py            # точка входа FastAPI, lifespan (таблицы + раннер тасков), роутеры
├── database.py            # engine, AsyncSessionFactory, get_db, Base — на уровне модуля
├── settings.py              # конфиг через .env (python-dotenv)
├── models.py                  # ВСЕ ORM-модели проекта
├── schemas.py                   # ВСЕ Pydantic-схемы проекта
├── modules/
│   ├── __init__.py                # сборка роутеров всех модулей в один api_router
│   ├── health.py                    # роутер healthcheck
│   └── users.py                       # роутер + сервис (только логика, без модели/схем)
├── tasks/
│   └── runner.py                       # агрегатор фоновых задач (asyncio.gather)
├── alembic/
│   ├── env.py                            # async-миграции, URL и metadata из settings/models
│   └── versions/
├── Dockerfile
├── docker-compose.yml                      # backend + Postgres, миграции накатываются автоматом
├── requirements.txt
└── .env.example
```

## Быстрый старт

### Docker (Postgres из коробки)

```bash
git clone <repo>
cd backend-template
docker compose up --build
```

Поднимутся два контейнера: Postgres+Backend. `alembic upgrade head`
автоматически при старте backend-контейнера, 
отдельно ничего запускать не нужно.

API: http://localhost:8000/docs

### Без Docker (SQLite)

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env

alembic upgrade head
uvicorn master:app --reload
```

Та же кодовая база, миграции — переключение между SQLite и
Postgres делается одной переменной `DATABASE_URL`, без правок.

`master.py` также создаёт таблицы напрямую из metadata при старте
(`Base.metadata.create_all`) — для случая, если контейнер/окружение
поднялось без миграций. Если миграции уже накатаны — это no-op, существующие
таблицы не трогает.

## Конфигурация (.env)

```
DATABASE_URL=sqlite+aiosqlite:///./dev.db
EXAMPLE_TASK_INTERVAL=30
```

`settings.py` грузит `.env` через `python-dotenv` и читает значения через
`os.getenv(KEY, default)` — обычные модульные константы, без отдельного
класса конфигурации. Импортируется как `import settings` →
`settings.DATABASE_URL`. В Docker `.env` не
участвует — `docker-compose.yml` задаёт `DATABASE_URL` напрямую через
`environment:`, `.env`/`load_dotenv()` там просто не находит файла и тихо
ничего не делает.

## Architecture Decisions

Почему выбраны именно эти технологии и паттерны.

### FastAPI, а не Flask/Django

Async-нативный (ASGI из коробки, не отдельный bolt-on), автоматическая
OpenAPI-документация и валидация запросов из типов через Pydantic — без
ручных сериализаторов, как в DRF. Для API это заметно меньше боилерплейта.

### Async SQLAlchemy, а не sync

Бэкенд (в примере продакшена) большую часть времени ждёт I/O — API ответы,
платёжных провайдеров, саму БД — а не считает на CPU. Async даёт одному
процессу обслуживать много параллельных запросов и фоновых тасков без
потока на соединение. Цена — код многословнее (`await` на каждый вызов, нет
ленивой подгрузки relationship "по требованию", всё нужно явно select'ить
заранее), трейсбеки читать сложнее, чем в sync-коде. Для CPU-bound
батч-обработки sync SQLAlchemy был бы проще и не медленнее.

### Alembic, а не только create_all()

`create_all()` отлично создаёт таблицы с нуля, но не умеет менять
существующую схему (добавить колонку, переименовать, накатить индекс) без
потери данных. Alembic даёт версионируемую историю изменений и
autogenerate, который сравнивает `models.py` с реальной БД и сам пишет
diff.

### Фоновые задачи через asyncio, а не Celery/RQ

Один процесс, корутины с `while True` + `asyncio.sleep`, собранные в
`tasks/runner.py` через `asyncio.gather` — без отдельного брокера
(Redis/RabbitMQ) и пула воркеров. Для нагрузки вида "проверить статус
платежа каждые N секунд" этого достаточно, и это на порядок меньше
операционной сложности, чем поднимать Celery ради пары периодических
джобов. Однако Celery/RQ можно задействовать позже, когда нагрузка увеличится.

### Модели и схемы отдельно от модулей

`modules/<name>.py` — только роутер и бизнес-логика (сервис). Модель — в
`models.py`, контракт API — в `schemas.py`. Так слои не путаются: открываешь
`modules/users.py` и видишь, что модуль должен выполнять. 
`models.py`/`schemas.py` — единые файлы, если проект не требовательный; 
вырастет — разбиваются на пакеты `models/`, `schemas/` с тем же
путём импорта (`from models import User`), без правок в остальном коде.

### database.py — синглтон без класса

`engine` и `AsyncSessionFactory` создаются один раз на уровне модуля при
импорте — Python кеширует модули, так что это уже синглтон без
дополнительного класса/`__new__`/metaclass. Обёртка в класс `Database` с
явным `__init__` добавила бы код, но не добавила гарантий — модуль и так
не пересоздастся при повторном импорте.

### settings.py через .env, без pydantic-settings

Плоские константы + `python-dotenv`, без отдельного класса конфигурации.
Для конфига в десяток переменных pydantic-settings (валидация типов,
nested-модели) — лишнее в начале; плюс плоский `import settings →
settings.DATABASE_URL` используется во всём остальном коде, а
pydantic-settings потребовал бы `from settings import settings` и доступ
через инстанс. Если конфиг разрастётся (обязательные поля с валидацией,
типизированные секреты, nested-структуры) — это сигнал мигрировать на
pydantic-settings.

## tasks/runner.py

Чтобы добавить фоновую задачу: вынести в отдельный файл `tasks/<name>.py`
как корутину со своим циклом и зарегистрировать вызов в `tasks/runner.py`
через `asyncio.gather` (по образцу `_example_task`). Почему через asyncio,
а не Celery — см. Architecture Decisions выше.

## Добавление нового модуля

1. Добавить модель в `models.py`, схемы — в `schemas.py`.
2. Создать `modules/<name>.py`: сервис с бизнес-логикой + `APIRouter`
   (по образцу `modules/users.py`).
3. Зарегистрировать роутер в `modules/__init__.py`.
4. `alembic revision --autogenerate -m "add <name> table"` → `alembic upgrade head`.

## Тесты

Пока не добавлены. Когда понадобятся:
`pytest` + `pytest-asyncio` + `httpx.AsyncClient` с оверрайдом `get_db` на
in-memory SQLite — добавляется отдельным шагом, не трогая структуру.

## Конец (v0.1)