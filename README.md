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

- `/start` — приветствие и список команд
- `/news` — последние новости из всех источников
- `/sources` — список источников
- `/settings` — текущие настройки

### Настройка через бота (админ)

Для ограничения доступа к настройкам задай переменную `ADMIN_ID` — свой
числовой ID (узнать можно у [@userinfobot](https://t.me/userinfobot)).
Без неё команды настройки доступны всем.

- `/addfeed URL [название]` — добавить RSS-источник
- `/autofeed адрес_сайта [название]` — автоматически найти RSS-ленту сайта
  (в т.ч. через RSSHub для YouTube, Twitter/X, Telegram, Instagram и др.)
  и добавить её
- `/rsshub адрес` — сменить инстанс RSSHub (см. ниже)
- `/removefeed номер` — удалить источник (номер из `/sources`)
- `/keywords слово1, слово2` — фильтр новостей по ключевым словам
  (пусто — отключить фильтр)
- `/regions Россия, США` — фильтр по упоминанию страны/региона в тексте
  новости (пусто — отключить фильтр)
- `/interval минуты` — интервал авто-проверки (минимум 1)
- `/broadcast on|off` — вкл/выкл авто-рассылку новостей в чат

Настройки сохраняются в файле `settings.json` (переменная `SETTINGS_FILE`),
изменения вступают в силу сразу, перезапуск не нужен.

В docker-compose настройки вынесены в папку `./data` на хосте (volume),
поэтому они **не теряются при обновлении стека**. Убедись, что папка
`data` лежит рядом с `docker-compose.yml` на NAS.

## Веб-интерфейс настроек

Вместе с ботом запускается веб-страница для управления настройками.

1. Открой в браузере `http://<IP_NAS>:8090`.
2. Задай пароль через переменную окружения `WEB_TOKEN` (иначе вход
   не потребуется). После установки пароль запрашивается при входе.

Порт по умолчанию — `8090` (переменные `WEB_HOST`, `WEB_PORT`).
В Portainer/OMV убедись, что порт `8090` открыт и проброшен в
`docker-compose.yml` (уже настроено).

## Сайты без RSS (RSSHub)

Если у сайта нет RSS-ленты (YouTube, Twitter/X, Telegram-каналы, Instagram,
Reddit и т.д.), автопоиск пробует получить ленту через RSSHub.

В `docker-compose.yml` бот работает вместе с собственным инстансом RSSHub
(сервис `rsshub`, образ `diygod/rsshub`). Бот автоматически использует его
по внутреннему адресу `http://rsshub:1200`, внешний порт RSSHub — `1200`
(можно открыть в браузере, чтобы проверить: `http://NAS:1200/telegram/channel/xxx`).

Если используешь внешний инстанс — смени адрес командой `/rsshub адрес`,
полем «RSSHub» в веб-интерфейсе или переменной `RSSHUB_BASE`.

## Настройка источников

Отредактируй список `RSS_FEEDS` в `config.py`:
имя источника и URL его RSS-ленты. Интервал авто-проверки —
`CHECK_INTERVAL_MINUTES` (по умолчанию 15 минут).
