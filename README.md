# ПР2. Визуализация зависимостей NuGet

Конфигурационное управление, РТУ МИРЭА. Вариант №14, УНБО-04-25.
Копылов Иван Алексеевич.

## Этап 1. Параметры

Минимальное CLI-приложение принимает имя пакета, адрес репозитория,
режим тестового файла, имя SVG, включение ASCII и исключаемую подстроку.
Дополнительно можно зафиксировать версию пакета, целевую платформу,
этап показа и максимальное число вершин.

```sh
./run.sh --package Serilog --stage 1
./run.sh --package '../bad' --stage 1
make test
```

Первый вызов выводит пары `ключ=значение`. Второй возвращает код 2
и сообщение об ошибке. На этом этапе запросов к NuGet ещё нет.

Код использует Python 3.9+ и стандартную библиотеку.

## Этап 2. Прямые зависимости

```sh
./run.sh --package Serilog --package-version '[3.1.1]' --stage 2
./run.sh --package Serilog.Sinks.Console --package-version '[6.0.0]' \
  --stage 2
```

Программа находит `PackageBaseAddress` в service index, самостоятельно
читает версии из JSON, загружает XML `.nuspec` и выбирает группу для
`net8.0`. Пустая группа означает, что для этой платформы зависимостей
нет. Группы разных платформ не смешиваются.

Для зависимости с диапазоном выбирается минимальная подходящая stable
версия; без закреплённой версии корня — последняя stable. Поддержаны
обычные интервалы NuGet, точная версия `[1.2.3]` и `1.*`.

Форматы: [NuGet API](https://learn.microsoft.com/en-us/nuget/api/overview),
[flat container](https://learn.microsoft.com/en-us/nuget/api/package-base-address-resource),
[диапазоны версий](https://learn.microsoft.com/en-us/nuget/concepts/package-versioning).

## Этап 3. Граф и нерекурсивный DFS

```sh
./run.sh --package A --test --repository examples/diamond.json --stage 3
./run.sh --package A --test --repository examples/cycle.json --stage 3
./run.sh --package A --test --repository examples/filter.json \
  --exclude SKIP --stage 3
```

Стек хранит ещё не посещённые вершины. Пакет отмечается посещённым до
обхода его детей. Поэтому цикл сохраняется на рисунке, но не зацикливает
программу, а общая зависимость D запрашивается один раз. Рёбра направлены
от пакета к его зависимостям. Фильтр не зависит от регистра и отсекает
всю ветвь исключённого пакета. Отдельный тест проходит цепочку из 1100
вершин без изменения ограничения рекурсии Python.

## Этап 4. Порядок загрузки

```sh
./run.sh --package A --test --repository examples/diamond.json --stage 4
./run.sh --package A --test --repository examples/cycle.json --stage 4
```

Для ромба получается `D -> B -> C -> A`: сначала общая зависимость D,
затем её потребители, в конце корневой пакет. Допустим и другой порядок,
если каждое ребро соблюдено. Для цикла программа возвращает код 1 и
показывает замкнутую цепочку: корректного топологического порядка нет.

Это порядок зависимостей, а не обещание повторить последовательность
HTTP-запросов `dotnet restore`: NuGet использует кэш и может скачивать
пакеты параллельно. Сравнение реальных результатов добавляется отдельно.

## Этап 5. Graphviz, SVG и ASCII

Нужна установленная команда `dot` из Graphviz.

```sh
./run.sh --package A --test --repository examples/diamond.json \
  --ascii --output diamond.svg
./run.sh --package A --test --repository examples/cycle.json \
  --ascii --output cycle.svg
./run.sh --package Serilog.Sinks.Console --package-version '[6.0.0]' \
  --ascii --output serilog.svg
```

Создаются текст `.dot` и настоящее SVG-изображение. `[повтор]` обозначает
общую зависимость, `[цикл]` — возврат в текущий путь. Наличие цикла не
мешает рисованию, но не позволяет получить порядок загрузки на этапе 4.
Результаты остаются локально и не попадают в Git как артефакты сборки.
