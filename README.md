Готово! Вот исправленный README — без скриншотов, с правильными ссылками и безопасным примером конфига:

```markdown
<div align="center">

# 🚀 Turbo Launcher

### Современный лаунчер для Minecraft с душой

[![Version](https://img.shields.io/badge/version-1.0.0-brightgreen.svg)](https://github.com/TurboTeamOfficial/turbo-launcher/releases)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-GPLv3-red.svg)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey)](https://github.com/TurboTeamOfficial/turbo-launcher)
[![Discord](https://img.shields.io/badge/chat-discord-7289da.svg)](https://discord.gg/ТВОЙ_СЕРВЕР)

![Turbo Launcher Banner](https://i.postimg.cc/TP0wZMDy/Turbo-Launcher-Preview.png)

</div>

---

## ✨ Особенности

<div align="center">

| 🎮 Игровые | ⚙️ Технические | 💬 Социальные |
|------------|----------------|---------------|
| Все версии Minecraft | Автоустановка Java | Discord Rich Presence |
| Fabric / Forge / Vanilla | Портативный режим | Онлайн-счётчик |
| Автоустановка модов | Умный выбор зеркал | Discord бот команды |
| Оптимизация FPS | Работа без интернета | Ely.by авторизация |

</div>

---

## 🎯 Что умеет лаунчер?

- ✅ **Поддержка 50+ версий** Minecraft (от 1.7.10 до 1.21+)
- ✅ **Автоматическая установка** Fabric, Forge
- ✅ **Умный установщик модов** (Sodium, Iris, Fabric API)
- ✅ **Встроенная Java** — качает нужную версию автоматически
- ✅ **Русский/English интерфейс**
- ✅ **Discord статус** — друзья видят, во что вы играете
- ✅ **Кроссплатформенность** — Windows, Linux, macOS
- ✅ **Никаких скрытых сборов** — полностью бесплатно

---

## 📋 Системные требования

### Минимальные:
| Компонент | Требование |
|-----------|-------------|
| **Операционная система** | Windows 10 / Linux / macOS |
| **Оперативная память** | 2 ГБ |
| **Свободное место на диске** | 500 МБ |
| **Интернет** | Только для первого запуска |

### Рекомендуемые:
| Компонент | Требование |
|-----------|-------------|
| **Операционная система** | Windows 11 |
| **Оперативная память** | 8 ГБ+ |
| **Свободное место на диске** | 5+ ГБ |
| **Процессор** | 4+ ядра |
| **Интернет** | Стабильное соединение |

---

## 🚀 Быстрый старт

### Для игроков (самый простой способ)

1. 📥 **Скачайте** последнюю версию из [Releases](https://github.com/TurboTeamOfficial/turbo-launcher/releases)
2. 📂 **Распакуйте** в любую папку (например, `C:\Games\TurboLauncher`)
3. 🖱️ **Запустите** `TurboLauncher.exe`
4. 🎮 **Выберите** версию и нажмите "ИГРАТЬ"

> 💡 **Совет:** Лаунчер портативный — можно носить на флешке!

### Для разработчиков

```bash
# Клонируем репозиторий
git clone https://github.com/TurboTeamOfficial/turbo-launcher.git
cd turbo-launcher

# Создаём виртуальное окружение
python -m venv venv
source venv/bin/activate  # Linux/Mac
# или
venv\Scripts\activate     # Windows

# Устанавливаем зависимости
pip install -r requirements.txt

# Запускаем
python launcher.py
```

---

## 🎮 Поддерживаемые загрузчики

| Загрузчик | Версии Minecraft | Статус |
|-----------|------------------|--------|
| **Vanilla** | Все версии | ✅ Полная поддержка |
| **Fabric** | 1.14+ (стабильно 1.16.5+) | ✅ Полная поддержка |
| **Forge** | 1.1+ (стабильно 1.12.2, 1.16.5+) | ✅ Полная поддержка |
| **OptiFine** | Планируется | 🚧 В разработке |
| **Quilt** | Планируется | 📋 В планах |

---

## 📦 Зависимости (для разработки)

```txt
pygame>=2.5.0
minecraft-launcher-lib>=5.0
pypresence>=4.3.0
psutil>=5.9.0
requests>=2.31.0
discord.py>=2.3.0
certifi>=2023.0.0
cryptography>=41.0.0
python-dotenv>=1.0.0
```

---

## 🛠️ Сборка из исходников

### Windows:
```batch
pip install pyinstaller
pyinstaller --onefile --windowed --name "TurboLauncher" ^
    --add-data "minecraft_title_cyrillic.ttf;." ^
    --add-data "minecraft.ttf;." ^
    --icon "icon.ico" ^
    --hidden-import pygame ^
    --hidden-import pypresence ^
    --hidden-import psutil ^
    --hidden-import discord ^
    launcher.py
```

### Linux / macOS:
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name "TurboLauncher" \
    --add-data "minecraft_title_cyrillic.ttf:." \
    --add-data "minecraft.ttf:." \
    --icon "icon.ico" \
    launcher.py
```

---

## 🔧 Конфигурация (для разработчиков)

Создайте файл `.env` для хранения секретов:

```env
DISCORD_APP_ID=your_app_id
DISCORD_BOT_TOKEN=your_bot_token
DISCORD_WEBHOOK_URL=your_webhook_url
JSONBIN_API_KEY=your_jsonbin_key
```

> ⚠️ **Важно:** 
> - Никогда не коммитьте реальные токены в репозиторий!
> - Добавьте `.env` в `.gitignore`
> - Для пользователей секреты уже вшиты в `.exe`

---

## 🤝 Как помочь проекту?

### 🐛 Сообщить об ошибке
[Создайте Issue](https://github.com/TurboTeamOfficial/turbo-launcher/issues) с описанием проблемы

### 💡 Предложить идею
Расскажите, как улучшить лаунчер в [Discussions](https://github.com/TurboTeamOfficial/turbo-launcher/discussions)

### 💻 Внести код
1. Форкните репозиторий
2. Создайте ветку (`git checkout -b feature/AmazingFeature`)
3. Сделайте коммит (`git commit -m 'Add AmazingFeature'`)
4. Запушьте (`git push origin feature/AmazingFeature`)
5. Откройте Pull Request

### 🌍 Помочь с переводами
Переведите лаунчер на свой язык в файле `lang.json`

---

## ❓ Частые вопросы

<details>
<summary><b>Лаунчер просит Java, что делать?</b></summary>

Лаунчер автоматически скачает нужную версию Java при первом запуске. Если что-то пошло не так — установите Java вручную с [официального сайта](https://www.java.com/download/).
</details>

<details>
<summary><b>Почему не работают моды?</b></summary>

Убедитесь, что:
1. Вы выбрали **Fabric** в загрузчике
2. Версия Minecraft **1.16.5 или выше**
3. В папке `mods` есть файлы `.jar`
</details>

<details>
<summary><b>Лаунчер не запускается на Linux</b></summary>

Установите зависимости:
```bash
sudo apt-get install python3-pygame python3-tk
```
</details>

<details>
<summary><b>Как сменить язык?</b></summary>

Нажмите на переключатель RU/EN в правом верхнем углу лаунчера.
</details>

<details>
<summary><b>Где сохраняются файлы игры?</b></summary>

В папке `.turbo_launcher` рядом с лаунчером. Всё портативно!
</details>

---

## 📄 Лицензия

Распространяется под лицензией **GNU GPLv3**. Смотрите файл [LICENSE](LICENSE) для деталей.

```
This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
GNU General Public License for more details.
```

---

## 🙏 Благодарности

- [minecraft-launcher-lib](https://github.com/JohannesGaessler/minecraft-launcher-lib) - библиотека для запуска Minecraft
- [Modrinth](https://modrinth.com/) - API для модов
- [Ely.by](https://ely.by/) - система авторизации
- [Adoptium](https://adoptium.net/) - сборки Java
- [PyGame](https://www.pygame.org/) - графический интерфейс
- [GitHub](https://github.com) - хостинг кода
- [PostImages](https://postimages.org/) - хостинг картинок

---

## 📞 Контакты

| Ссылка | Описание |
|--------|----------|
| [![Discord](https://img.shields.io/badge/Discord-7289DA?style=for-the-badge&logo=discord&logoColor=white)](https://discord.gg/ТВОЙ_СЕРВЕР) | Наш Discord сервер |
| [![GitHub Issues](https://img.shields.io/badge/GitHub%20Issues-181717?style=for-the-badge&logo=github&logoColor=white)](https://github.com/TurboTeamOfficial/turbo-launcher/issues) | Сообщить о проблеме |
| [![Telegram](https://img.shields.io/badge/Telegram-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/ТВОЙ_ТЕЛЕГРАМ) | Telegram канал (опционально) |

---

<div align="center">

### ⭐ Поставьте звезду, если вам нравится проект! ⭐

**Сделано с ❤️ для Minecraft сообщества**

</div>
