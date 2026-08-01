# DailyNews — простой новостной агрегатор (Telegram-бот)

Собирает новости из RSS-лент и присылает их в Telegram.

## Установка

```bash
pip install -r requirements.txt
```

## Настройка

1. Создай бота через [@BotFather](https://t.me/BotFather) и получи токен.
2. Задай переменные окружения (Windows PowerShell):

```powershell
$env:BOT_TOKEN = "твой_токен"
$env:CHAT_ID = "свой_telegram_id"
```

`CHAT_ID` нужен для авто-рассылки новых новостей. Можно узнать через бота
[@userinfobot](https://t.me/userinfobot).

## Запуск

```bash
python bot.py
```

## Запуск через Docker (OpenMediaVault 8)

### Вариант A: Portainer (рекомендуется)

Установи Portainer на OMV (из раздела Plugins или официальный контейнер),
подключи его к Docker. Дальше:

1. Создай репозиторий на GitHub/Gitea/GitLab и залей в него
   содержимое этой папки (`bot.py`, `config.py`, `aggregator.py`,
   `requirements.txt`, `Dockerfile`, `docker-compose.yml`).
   `.env` в репозиторий не попадёт (см. `.gitignore`).

2. В Portainer: **Stacks → Add stack → Git repository**.
   Укажи URL репозитория — Portainer склонирует проект, увидит
   `docker-compose.yml` с `build: .` и соберёт образ сам.

3. В разделе Environment Variables добавь:

```bash
BOT_TOKEN=твой_токен
CHAT_ID=свой_telegram_id
```

4. Нажми **Deploy**. Контейнер появится в разделе **Containers**.
   Обновления бота: `git push` → в Portainer открой стек → **Update**.

### Вариант B: без Portainer, через плагин Compose OMV 8

В OMV 8 нет раздела «Stacks» — плагин Compose переработан,
всё управление файлами происходит через **Services → Compose → Files**.
Сборка `build: .` из UI не работает, поэтому нужен готовый образ:

1. Собери и запушь образ (замени `USERNAME` на свой Docker Hub):

```bash
docker build -t USERNAME/dailynews:latest .
docker push USERNAME/dailynews:latest
```

2. В `docker-compose.yml` замени `build: .` на `image: USERNAME/dailynews:latest`.

3. На OMV: **Services → Compose → Files → Add**, вставь содержимое
   `docker-compose.yml` как файл, отметь галочку «Show environment file»
   и добавь в поле Environment `BOT_TOKEN` и `CHAT_ID`.

4. Выдели созданный файл в списке и нажми кнопку **up** (стрелка вверх).

Контейнер стартует автоматически при загрузке системы (`restart: unless-stopped`).
Логи: кнопка **Tools → logs** напротив файла.

## Команды

- `/start` — приветствие
- `/news` — последние новости из всех источников
- `/sources` — список источников

## Настройка источников

Отредактируй список `RSS_FEEDS` в `config.py`:
имя источника и URL его RSS-ленты. Интервал авто-проверки —
`CHECK_INTERVAL_MINUTES` (по умолчанию 15 минут).
