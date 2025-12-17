# Создайте папку проекта
mkdir tank_calculator_bot
cd tank_calculator_bot

# Создайте виртуальное окружение
python -m venv venv

# Активируйте его (Windows)
venv\Scripts\activate
# или (Mac/Linux)
source venv/bin/activate

# Установите зависимости
pip install python-telegram-bot python-dotenv