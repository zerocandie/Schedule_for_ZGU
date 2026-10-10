# Расписание студентов ЗГУ

Статический сайт кафедры ИСИТ. Публикуется на GitHub Pages из ветки `main`.

Адрес: https://zerocandie.github.io/Schedule_for_ZGU/

## Публикация

1. Запушить ветку `main`.
2. В репозитории открыть **Settings → Pages → Build and deployment** и выбрать источник **GitHub Actions**.
3. Workflow [`.github/workflows/pages.yml`](.github/workflows/pages.yml) выкладывает сайт при каждом пуше в `main`. Его можно запустить и вручную со вкладки Actions.

Файл `.nojekyll` отключает Jekyll: страницы, скрипты и таблицы Excel отдаются как есть. Ссылки в сайте относительные, поэтому он открывается и по адресу проекта с префиксом `/Schedule_for_ZGU/`.
