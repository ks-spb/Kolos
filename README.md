# Kolos_v3

## Launcher

Для запуска через отдельное диалоговое окно:

```bash
python launcher.py
```

Кнопки лаунчера:

- `Запустить Колос` — запускает `main.py` в отдельной консоли Windows.
- `Запустить Glaz` — запускает `Glaz/main.py` в отдельной консоли Windows.
- `Остановить` — завершает оба процесса (Kolos и Glaz).

## Интерактивный просмотр графа памяти

Просмотрщик `graph_viewer.py` читает таблицы `tochki` и `svyazi` напрямую из
`db_v4.db` в режиме только чтения. Он группирует повторные связи одного
направления, подписывает вершины и стрелки, создаёт автономный
`kolos_graph.html` и открывает его в браузере.

Установка и запуск из корня проекта:

```bash
python -m pip install -r requirements.txt
python graph_viewer.py
```

Для запуска двойным щелчком используйте файл
`Запустить граф Kolos.bat` в корне проекта.

Дополнительные параметры:

```bash
python graph_viewer.py --database D:\data\memory.db
python graph_viewer.py --output D:\reports\kolos.html --no-open
```

Путь к другой базе также можно указать через `KOLOS_GRAPH_DATABASE_PATH`.
Отсутствующая база не создаётся. Существующий статический просмотрщик
`Diagram_new.py` продолжает работать независимо.

