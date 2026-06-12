# Claude Code Impact Dashboard

Анализирует влияние Claude Code на команду, сравнивая Q1 (без CC) и Q2 (с CC).

## Быстрый старт

### 1. Установить зависимости
```bash
pip install -r requirements.txt
```

### 2. Настроить окружение
```bash
cp .env.example .env
# Заполни JIRA_URL, JIRA_USER, JIRA_TOKEN, GITLAB_URL, GITLAB_TOKEN
```

### 3. Найти ID кастомного поля Team Link
```bash
python main.py --find-fields | grep -i team
# Скопируй нужный customfield_XXXXX в .env → JIRA_TEAM_FIELD
```

### 4. Добавить участников команды

Открой `config.py` и заполни список `TEAM_MEMBERS`:

```python
TEAM_MEMBERS = [
    Member(
        name="Ivan Petrov",
        role="dev",                         # "dev" или "qa"
        jira_account_id="5f3eabc...",       # из Jira URL профиля
        gitlab_username="ivan.petrov",
        color="#6366f1",                    # цвет аватара
    ),
]
```

**Как найти Jira accountId:**
- Открой профиль пользователя в Jira
- В URL будет: `.../jira/people/<accountId>`

**Как найти GitLab username:**
- Логин пользователя в GitLab (не email)

### 5. Запустить
```bash
python main.py                  # генерирует dashboard.html
python main.py --no-cache       # сбросить кэш и перефетчить
python main.py --output my.html # кастомное имя файла
```

## Переменные окружения

| Переменная | Обязательная | Описание |
|---|---|---|
| `JIRA_URL` | ✓ | Базовый URL Jira, напр. `https://jira.corp.com` |
| `JIRA_USER` | ✓ | Email для аутентификации |
| `JIRA_TOKEN` | ✓ | API-токен (Settings → Security → API tokens) |
| `JIRA_PROJECT` | ✓ | Project key, напр. `QBS` |
| `JIRA_TEAM_FIELD` | — | ID кастомного поля Team, напр. `customfield_10100` |
| `JIRA_TEAM_VALUE` | — | Значение фильтра, напр. `Backend Core` |
| `GITLAB_URL` | ✓ | Базовый URL GitLab, напр. `https://gitlab.corp.com` |
| `GITLAB_TOKEN` | ✓ | Personal Access Token (scopes: `read_api`) |
| `GITLAB_GROUP` | ✓ | Путь группы, напр. `company/backend` |
| `Q1_START` / `Q1_END` | — | Период Q1 (default: 2025-01-01 / 2025-03-31) |
| `Q2_START` / `Q2_END` | — | Период Q2 (default: 2025-04-01 / 2025-06-30) |

## Кэш

Все API-ответы кэшируются в `.cache/` в виде JSON.  
При изменении состава команды или периодов — запусти `--no-cache`.

## Структура проекта

```
├── main.py          # точка входа
├── config.py        # конфиг + список команды
├── fetch_jira.py    # Jira REST API клиент
├── fetch_gitlab.py  # GitLab REST API клиент
├── analyze.py       # вычисление метрик
├── dashboard.py     # генерация HTML
├── requirements.txt
└── .env.example
```
