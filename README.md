# Claude Code Impact Dashboard

Сравнивает команду Q1 (без Claude Code) и Q2 (с Claude Code).  
Источники данных: **Jira** (эпики + задачи по статусам) + **GitLab** (MR, коммиты, комментарии к ревью).

## Быстрый старт

```bash
pip install -r requirements.txt
cp .env.example .env
# Заполни .env — см. таблицу ниже
python main.py
# → открыть dashboard.html в браузере
```

## Настройка .env

| Переменная | Обязательная | Описание |
|---|---|---|
| `JIRA_URL` | ✓ | `https://jira.corp.com` |
| `JIRA_USER` | ✓ | Email для Basic Auth |
| `JIRA_TOKEN` | ✓ | Jira API token |
| `JIRA_PROJECT` | ✓ | Project key, напр. `QBS` |
| `JIRA_TEAM_FIELD` | — | ID кастомного поля команды (найти: `python main.py --find-fields`) |
| `JIRA_TEAM_VALUE` | — | Значение фильтра, напр. `Backend Core` |
| `GITLAB_URL` | ✓ | `https://gitlab.corp.com` |
| `GITLAB_TOKEN` | ✓ | Personal Access Token (scope: `read_api`) |
| `GITLAB_GROUP` | ✓ | Путь группы, напр. `company/backend` |
| `GITLAB_USERNAMES` | ✓ | Юзернеймы GitLab через запятую: `ivan.petrov,anna.sidorova` |
| `Q1_START` / `Q1_END` | — | Период Q1 (default: 2025-01-01 / 2025-03-31) |
| `Q2_START` / `Q2_END` | — | Период Q2 (default: 2025-04-01 / 2025-06-30) |

## Полезные команды

```bash
# Найти ID кастомного поля "Team Link" в Jira
python main.py --find-fields | grep -i team

# Сбросить кэш и перефетчить данные заново
python main.py --no-cache

# Кастомное имя выходного файла
python main.py --output my_report.html
```

## Кэш

Все ответы API сохраняются в `.cache/` (JSON).  
Повторный запуск использует кэш — без новых API-запросов.  
При изменении состава команды или периодов запусти `--no-cache`.

## Структура

```
├── main.py          # точка входа
├── config.py        # конфиг (читает .env + GITLAB_USERNAMES)
├── fetch_jira.py    # Jira REST API v2
├── fetch_gitlab.py  # GitLab REST API v4 (агрегат по команде)
├── analyze.py       # вычисление метрик
├── dashboard.py     # генерация HTML из данных
├── requirements.txt
└── .env.example
```
