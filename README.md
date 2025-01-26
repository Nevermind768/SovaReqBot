# Feedback-Bot
Телеграмм бот для получения обращений жителей города.

## Как запустить?
Создать в корне проекта `.env` файл и заполнить его по шаблону `.env.example`.
Настроить СУБД PostgreSql, данные авторизации прописать в соответствующих полях `.env`.

Для запуска бота:
1. Создайте структуру:
```
Feedback-Bot
├── update.zsh
└── data
    ├── logs
    └── .env
```
2. В папке `Feedback-Bot/data` настройте `.env` и сгенерируйте ключи командой
`openssl req -x509 -newkey rsa:4096 -nodes -out cert.pem -keyout key.pem -days 365`
1. Запустите файл `Feedback-Bot/update.zsh`
