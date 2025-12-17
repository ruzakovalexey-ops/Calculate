import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from calculator import (
    TankCalculator, TankParams, AdditionalSheet, AdditionalOptions,
    TankType, MaterialType, PressureType, HEIGHT_OPTIONS
)

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния разговора
(
    SELECT_TANK_TYPE,
    INPUT_VOLUME,
    SELECT_HEIGHT,
    SELECT_MATERIAL,
    INPUT_THICKNESS,
    INPUT_ANGLES,
    SELECT_PRESSURE,
    ADDITIONAL_SHEETS,
    ADDITIONAL_OPTIONS,
    INPUT_COMPLEXITY,
    CALCULATE
) = range(11)

# Хранение данных пользователя
user_data: Dict[int, Dict[str, Any]] = {}


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало работы с ботом."""
    user_id = update.effective_user.id
    
    # Инициализация данных пользователя
    user_data[user_id] = {
        'params': TankParams(
            volume=1000,
            height=1000,
            thickness_cylinder=3,
            thickness_top=3,
            thickness_bottom=4,
            angle_top=90,
            angle_bottom=90,
            material='304',
            tank_type='single',
            pressure=1
        ),
        'calculator': TankCalculator(),
        'current_sheet': None,
        'sheets': [],
        'options': AdditionalOptions()
    }
    
    await update.message.reply_text(
        "👋 Добро пожаловать в калькулятор стоимости емкостей из нержавеющей стали!\n\n"
        "Я помогу вам рассчитать стоимость изготовления емкости по заданным параметрам.\n\n"
        "Давайте начнем! Выберите тип емкости:",
        reply_markup=get_tank_type_keyboard()
    )
    
    return SELECT_TANK_TYPE


def get_tank_type_keyboard():
    """Клавиатура для выбора типа емкости."""
    keyboard = [
        [
            InlineKeyboardButton("Одностенная", callback_data="tank_single"),
            InlineKeyboardButton("С кожухом", callback_data="tank_insulated"),
        ],
        [
            InlineKeyboardButton("С рубашкой", callback_data="tank_double"),
            InlineKeyboardButton("Котел", callback_data="tank_boiler"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def tank_type_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора типа емкости."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    tank_type = query.data.replace("tank_", "")
    
    user_data[user_id]['params'].tank_type = tank_type
    
    await query.edit_message_text(
        f"✅ Выбран тип: {get_tank_type_name(tank_type)}\n\n"
        "Введите объем емкости в литрах (например: 1000):"
    )
    
    return INPUT_VOLUME


def get_tank_type_name(tank_type: str) -> str:
    """Получение читаемого названия типа емкости."""
    names = {
        'single': 'Одностенная',
        'insulated': 'С теплоизоляционным кожухом',
        'double': 'С рубашкой',
        'boiler': 'Варочный котел'
    }
    return names.get(tank_type, tank_type)


async def input_volume(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода объема."""
    user_id = update.effective_user.id
    
    try:
        volume = float(update.message.text)
        if volume <= 0:
            await update.message.reply_text("❌ Объем должен быть больше 0. Попробуйте еще раз:")
            return INPUT_VOLUME
            
        user_data[user_id]['params'].volume = volume
        
        await update.message.reply_text(
            f"✅ Объем: {volume} л\n\n"
            "Выберите высоту цилиндра в мм:",
            reply_markup=get_height_keyboard()
        )
        
        return SELECT_HEIGHT
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число. Попробуйте еще раз:")
        return INPUT_VOLUME


def get_height_keyboard():
    """Клавиатура для выбора высоты."""
    keyboard = []
    row = []
    
    for i, height in enumerate(HEIGHT_OPTIONS[:12], 1):  # Показываем первые 12 значений
        row.append(InlineKeyboardButton(f"{height} мм", callback_data=f"height_{height}"))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку для ввода произвольной высоты
    keyboard.append([InlineKeyboardButton("Другая высота", callback_data="height_custom")])
    
    return InlineKeyboardMarkup(keyboard)


async def height_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора высоты."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "height_custom":
        await query.edit_message_text("Введите высоту цилиндра в мм:")
        return SELECT_HEIGHT
    
    height = float(query.data.replace("height_", ""))
    user_data[user_id]['params'].height = height
    
    await query.edit_message_text(
        f"✅ Высота: {height} мм\n\n"
        "Выберите материал внутренней емкости:",
        reply_markup=get_material_keyboard()
    )
    
    return SELECT_MATERIAL


async def custom_height(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода произвольной высоты."""
    user_id = update.effective_user.id
    
    try:
        height = float(update.message.text)
        if height <= 0:
            await update.message.reply_text("❌ Высота должна быть больше 0. Попробуйте еще раз:")
            return SELECT_HEIGHT
            
        user_data[user_id]['params'].height = height
        
        await update.message.reply_text(
            f"✅ Высота: {height} мм\n\n"
            "Выберите материал внутренней емкости:",
            reply_markup=get_material_keyboard()
        )
        
        return SELECT_MATERIAL
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число. Попробуйте еще раз:")
        return SELECT_HEIGHT


def get_material_keyboard():
    """Клавиатура для выбора материала."""
    keyboard = [
        [
            InlineKeyboardButton("AISI 304 (350 руб/кг)", callback_data="material_304"),
            InlineKeyboardButton("AISI 316 (650 руб/кг)", callback_data="material_316"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def material_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора материала."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    material = query.data.replace("material_", "")
    
    user_data[user_id]['params'].material = material
    
    # Если выбран котел, запрашиваем давление
    if user_data[user_id]['params'].tank_type == 'boiler':
        await query.edit_message_text(
            f"✅ Материал: AISI {material}\n\n"
            "Выберите давление в рубашке котла:",
            reply_markup=get_pressure_keyboard()
        )
        return SELECT_PRESSURE
    
    await query.edit_message_text(
        f"✅ Материал: AISI {material}\n\n"
        "Введите толщины стенок в мм через пробел (цилиндр верх низ):\n"
        "Например: 3 3 4"
    )
    
    return INPUT_THICKNESS


def get_pressure_keyboard():
    """Клавиатура для выбора давления (только для котла)."""
    keyboard = [
        [
            InlineKeyboardButton("Без избыточного давления", callback_data="pressure_1"),
        ],
        [
            InlineKeyboardButton("До 2 атм", callback_data="pressure_2"),
            InlineKeyboardButton("Свыше 3 атм", callback_data="pressure_3"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def pressure_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора давления."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    pressure = int(query.data.replace("pressure_", ""))
    
    user_data[user_id]['params'].pressure = pressure
    
    await query.edit_message_text(
        f"✅ Давление: {get_pressure_name(pressure)}\n\n"
        "Введите толщины стенок в мм через пробел (цилиндр верх низ):\n"
        "Например: 3 3 4"
    )
    
    return INPUT_THICKNESS


def get_pressure_name(pressure: int) -> str:
    """Получение читаемого названия давления."""
    names = {
        1: 'Без избыточного давления',
        2: 'До 2 атм',
        3: 'Свыше 3 атм (толщина 4 мм)'
    }
    return names.get(pressure, str(pressure))


async def input_thickness(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода толщин."""
    user_id = update.effective_user.id
    
    try:
        parts = update.message.text.split()
        if len(parts) != 3:
            raise ValueError
        
        thickness_cylinder = float(parts[0])
        thickness_top = float(parts[1])
        thickness_bottom = float(parts[2])
        
        if any(t <= 0 for t in [thickness_cylinder, thickness_top, thickness_bottom]):
            await update.message.reply_text("❌ Толщины должны быть больше 0. Попробуйте еще раз:")
            return INPUT_THICKNESS
        
        user_data[user_id]['params'].thickness_cylinder = thickness_cylinder
        user_data[user_id]['params'].thickness_top = thickness_top
        user_data[user_id]['params'].thickness_bottom = thickness_bottom
        
        await update.message.reply_text(
            f"✅ Толщины: цилиндр={thickness_cylinder}мм, верх={thickness_top}мм, низ={thickness_bottom}мм\n\n"
            "Введите углы раствора конусов через пробел (верх низ) в градусах:\n"
            "Например: 90 90"
        )
        
        return INPUT_ANGLES
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите 3 числа через пробел. Попробуйте еще раз:")
        return INPUT_THICKNESS


async def input_angles(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода углов."""
    user_id = update.effective_user.id
    
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            raise ValueError
        
        angle_top = float(parts[0])
        angle_bottom = float(parts[1])
        
        if not (0 < angle_top < 180 and 0 < angle_bottom < 180):
            await update.message.reply_text("❌ Углы должны быть между 0 и 180 градусами. Попробуйте еще раз:")
            return INPUT_ANGLES
        
        user_data[user_id]['params'].angle_top = angle_top
        user_data[user_id]['params'].angle_bottom = angle_bottom
        
        await update.message.reply_text(
            f"✅ Углы: верх={angle_top}°, низ={angle_bottom}°\n\n"
            "Хотите добавить дополнительные листы нержавейки?",
            reply_markup=get_yes_no_keyboard("sheets")
        )
        
        return ADDITIONAL_SHEETS
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите 2 числа через пробел. Попробуйте еще раз:")
        return INPUT_ANGLES


def get_yes_no_keyboard(context: str):
    """Клавиатура Да/Нет."""
    keyboard = [
        [
            InlineKeyboardButton("Да", callback_data=f"{context}_yes"),
            InlineKeyboardButton("Нет", callback_data=f"{context}_no"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def additional_sheets_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка решения о добавлении листов."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "sheets_yes":
        await query.edit_message_text(
            "Введите данные листа в формате:\n"
            "материал размер толщина количество\n\n"
            "Пример: 304 1000x2000 3 2\n\n"
            "Доступные размеры: 1000x2000, 1250x2500, 1500x3000"
        )
        return ADDITIONAL_SHEETS
    else:
        await query.edit_message_text(
            "Хотите добавить дополнительное оборудование?",
            reply_markup=get_yes_no_keyboard("options")
        )
        return ADDITIONAL_OPTIONS


async def add_sheet(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка добавления листа."""
    user_id = update.effective_user.id
    
    try:
        parts = update.message.text.split()
        if len(parts) != 4:
            raise ValueError
        
        material = parts[0]
        size = parts[1]
        thickness = float(parts[2])
        quantity = int(parts[3])
        
        if material not in ['304', '316']:
            await update.message.reply_text("❌ Материал должен быть 304 или 316. Попробуйте еще раз:")
            return ADDITIONAL_SHEETS
        
        if size not in ['1000x2000', '1250x2500', '1500x3000']:
            await update.message.reply_text("❌ Неверный размер. Доступные: 1000x2000, 1250x2500, 1500x3000:")
            return ADDITIONAL_SHEETS
        
        if thickness <= 0 or quantity <= 0:
            await update.message.reply_text("❌ Толщина и количество должны быть больше 0. Попробуйте еще раз:")
            return ADDITIONAL_SHEETS
        
        sheet = AdditionalSheet(material, size, thickness, quantity)
        user_data[user_id]['calculator'].additional_sheets.append(sheet)
        
        await update.message.reply_text(
            f"✅ Добавлен лист: AISI {material}, {size}, {thickness}мм, {quantity}шт\n\n"
            "Добавить еще один лист? (введите 'готово' для продолжения или новые данные листа):"
        )
        
        return ADDITIONAL_SHEETS
        
    except ValueError:
        await update.message.reply_text("❌ Неверный формат. Попробуйте еще раз:")
        return ADDITIONAL_SHEETS


async def sheets_done(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершение добавления листов."""
    if update.message.text.lower() == 'готово':
        await update.message.reply_text(
            "Хотите добавить дополнительное оборудование?",
            reply_markup=get_yes_no_keyboard("options")
        )
        return ADDITIONAL_OPTIONS
    else:
        # Пытаемся добавить еще один лист
        return await add_sheet(update, context)


async def additional_options_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка решения о добавлении оборудования."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "options_yes":
        await query.edit_message_text(
            "Выберите дополнительное оборудование:\n"
            "(можно выбрать несколько, затем нажать 'Готово')",
            reply_markup=get_options_keyboard()
        )
        return ADDITIONAL_OPTIONS
    else:
        await query.edit_message_text(
            "Введите коэффициент сложности (по умолчанию 3.5):"
        )
        return INPUT_COMPLEXITY


def get_options_keyboard():
    """Клавиатура для выбора дополнительного оборудования."""
    keyboard = [
        [
            InlineKeyboardButton("Люк круглый DN400 (+30 000 руб)", callback_data="option_luk400"),
        ],
        [
            InlineKeyboardButton("Люк круглый DN500 (+40 000 руб)", callback_data="option_luk500"),
        ],
        [
            InlineKeyboardButton("Уровнемер (+12 000 руб)", callback_data="option_level"),
        ],
        [
            InlineKeyboardButton("Дисковый затвор до DN50 (+6 000 руб)", callback_data="option_valve"),
        ],
        [
            InlineKeyboardButton("Готово", callback_data="options_done"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def option_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка выбора опции."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    
    if query.data == "options_done":
        await query.edit_message_text(
            "Введите коэффициент сложности (по умолчанию 3.5):"
        )
        return INPUT_COMPLEXITY
    
    # Переключаем состояние выбранной опции
    option_name = query.data.replace("option_", "")
    
    if option_name == "luk400":
        user_data[user_id]['calculator'].options.luk400 = not user_data[user_id]['calculator'].options.luk400
    elif option_name == "luk500":
        user_data[user_id]['calculator'].options.luk500 = not user_data[user_id]['calculator'].options.luk500
    elif option_name == "level":
        user_data[user_id]['calculator'].options.level = not user_data[user_id]['calculator'].options.level
    elif option_name == "valve":
        user_data[user_id]['calculator'].options.valve = not user_data[user_id]['calculator'].options.valve
    
    # Обновляем сообщение с текущим состоянием
    status_text = get_options_status(user_data[user_id]['calculator'].options)
    
    await query.edit_message_text(
        f"Выберите дополнительное оборудование:\n\n{status_text}",
        reply_markup=get_options_keyboard()
    )
    
    return ADDITIONAL_OPTIONS


def get_options_status(options: AdditionalOptions) -> str:
    """Получение текста статуса опций."""
    status = []
    if options.luk400:
        status.append("✅ Люк DN400")
    if options.luk500:
        status.append("✅ Люк DN500")
    if options.level:
        status.append("✅ Уровнемер")
    if options.valve:
        status.append("✅ Затвор DN50")
    
    if not status:
        return "Не выбрано"
    
    return "\n".join(status)


async def input_complexity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработка ввода коэффициента сложности."""
    user_id = update.effective_user.id
    
    try:
        complexity = float(update.message.text)
        if not (1 <= complexity <= 10):
            await update.message.reply_text("❌ Коэффициент должен быть от 1 до 10. Попробуйте еще раз:")
            return INPUT_COMPLEXITY
        
        user_data[user_id]['calculator'].complexity_coefficient = complexity
        
        # Выполняем расчет
        await calculate_and_show_results(update, context)
        
        return ConversationHandler.END
        
    except ValueError:
        await update.message.reply_text("❌ Пожалуйста, введите число. Попробуйте еще раз:")
        return INPUT_COMPLEXITY


async def calculate_and_show_results(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Выполнение расчета и вывод результатов."""
    user_id = update.effective_user.id
    
    try:
        # Получаем данные пользователя
        params = user_data[user_id]['params']
        calculator = user_data[user_id]['calculator']
        
        # Выполняем расчет
        results = calculator.calculate(params)
        
        # Формируем сообщение с результатами
        message = format_results_message(results, params)
        
        # Отправляем результаты
        if update.callback_query:
            await update.callback_query.message.reply_text(message, parse_mode='HTML')
        else:
            await update.message.reply_text(message, parse_mode='HTML')
            
        # Предлагаем начать новый расчет
        keyboard = [[InlineKeyboardButton("🔄 Новый расчет", callback_data="new_calculation")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "Хотите выполнить новый расчет?",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "Хотите выполнить новый расчет?",
                reply_markup=reply_markup
            )
            
    except Exception as e:
        logger.error(f"Ошибка расчета: {e}")
        error_msg = "❌ Произошла ошибка при расчете. Пожалуйста, попробуйте еще раз."
        
        if update.callback_query:
            await update.callback_query.message.reply_text(error_msg)
        else:
            await update.message.reply_text(error_msg)


def format_results_message(results: Dict, params: TankParams) -> str:
    """Форматирование сообщения с результатами."""
    geometry = results['geometry']
    
    message = (
        f"<b>📊 РЕЗУЛЬТАТЫ РАСЧЕТА</b>\n"
        f"<i>Тип емкости:</i> {get_tank_type_name(params.tank_type)}\n"
        f"<i>Объем:</i> {params.volume:.0f} л\n"
        f"<i>Высота цилиндра:</i> {params.height:.0f} мм\n"
        f"<i>Материал:</i> AISI {params.material}\n\n"
        
        f"<b>📐 Геометрические параметры:</b>\n"
        f"• Диаметр емкости: {geometry.diameter * 1000:.1f} мм\n"
        f"• Высота цилиндра: {geometry.height * 1000:.1f} мм\n"
        f"• Общий вес: {results['total_weight']:.1f} кг\n\n"
        
        f"<b>💰 Стоимость материалов емкости:</b>\n"
    )
    
    # Материалы емкости
    for material in results['materials'][:5]:  # Показываем первые 5 материалов
        message += f"• {material.name}: {material.weight:.1f} кг × {material.price_per_kg} руб/кг = {material.cost:.0f} руб\n"
    
    if len(results['materials']) > 5:
        message += f"• ... и ещё {len(results['materials']) - 5} позиций\n"
    
    message += f"<b>Итого материалы емкости:</b> {results['tank_cost']:.0f} руб\n\n"
    
    # Дополнительные листы
    if results['sheet_materials']:
        message += f"<b>📄 Дополнительные листы:</b>\n"
        for sheet in results['sheet_materials']:
            message += f"• {sheet.name}: {sheet.cost:.0f} руб\n"
        message += f"<b>Итого листы:</b> {results['sheets_cost']:.0f} руб\n\n"
    
    # Дополнительное оборудование
    if results['option_materials']:
        message += f"<b>🔧 Дополнительное оборудование:</b>\n"
        for option in results['option_materials']:
            message += f"• {option.name}: {option.cost:.0f} руб\n"
        message += f"<b>Итого опции:</b> {results['options_cost']:.0f} руб\n\n"
    
    # Итоги
    message += (
        f"<b>📈 Коэффициент сложности:</b> {results['complexity']:.1f}\n"
        f"<b>Стоимость материалов × коэффициент:</b> {results['cost_with_complexity']:.0f} руб\n"
        f"<b>Опции × 2.5:</b> {results['options_cost_multiplied']:.0f} руб\n\n"
        
        f"<b>🎯 ИТОГОВАЯ СТОИМОСТЬ:</b>\n"
        f"<b><u>{results['final_cost']:.0f} руб</u></b>"
    )
    
    return message


async def new_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начало нового расчета."""
    query = update.callback_query
    await query.answer()
    
    return await start(update, context)


async def quick_calculation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Быстрый расчет с параметрами по умолчанию."""
    user_id = update.effective_user.id
    
    # Используем параметры по умолчанию
    params = TankParams(
        volume=1000,
        height=1000,
        thickness_cylinder=3,
        thickness_top=3,
        thickness_bottom=4,
        angle_top=90,
        angle_bottom=90,
        material='304',
        tank_type='single',
        pressure=1
    )
    
    calculator = TankCalculator()
    
    # Выполняем расчет
    results = calculator.calculate(params)
    
    # Формируем сообщение
    message = format_results_message(results, params)
    
    await update.message.reply_text(message, parse_mode='HTML')


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показать справку."""
    help_text = (
        "🤖 <b>Калькулятор стоимости емкостей из нержавеющей стали</b>\n\n"
        
        "Доступные команды:\n"
        "/start - начать новый расчет\n"
        "/quick - быстрый расчет с параметрами по умолчанию\n"
        "/help - показать эту справку\n\n"
        
        "<b>Процесс расчета:</b>\n"
        "1. Выберите тип емкости\n"
        "2. Введите объем\n"
        "3. Выберите высоту\n"
        "4. Выберите материал\n"
        "5. Введите толщины стенок\n"
        "6. Введите углы конусов\n"
        "7. Добавьте листы (опционально)\n"
        "8. Добавьте оборудование (опционально)\n"
        "9. Введите коэффициент сложности\n"
        "10. Получите результат!\n\n"
        
        "<b>Примечания:</b>\n"
        "• Рубашка: +40 мм к внутреннему диаметру\n"
        "• Теплоизоляционный кожух: +90 мм\n"
        "• Угол конуса - угол раствора"
    )
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена диалога."""
    await update.message.reply_text(
        "Расчет отменен. Для нового расчета используйте /start"
    )
    return ConversationHandler.END


def main():
    """Запуск бота."""
    # Получаем токен из переменных окружения
    TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
    if not TOKEN:
        raise ValueError("Не задан TELEGRAM_BOT_TOKEN в переменных окружения")
    
    # Создаем приложение
    application = Application.builder().token(TOKEN).build()
    
    # Создаем обработчик диалога
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            SELECT_TANK_TYPE: [
                CallbackQueryHandler(tank_type_selected, pattern='^tank_')
            ],
            INPUT_VOLUME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_volume)
            ],
            SELECT_HEIGHT: [
                CallbackQueryHandler(height_selected, pattern='^height_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, custom_height)
            ],
            SELECT_MATERIAL: [
                CallbackQueryHandler(material_selected, pattern='^material_')
            ],
            SELECT_PRESSURE: [
                CallbackQueryHandler(pressure_selected, pattern='^pressure_')
            ],
            INPUT_THICKNESS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_thickness)
            ],
            INPUT_ANGLES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_angles)
            ],
            ADDITIONAL_SHEETS: [
                CallbackQueryHandler(additional_sheets_decision, pattern='^sheets_'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, add_sheet)
            ],
            ADDITIONAL_OPTIONS: [
                CallbackQueryHandler(additional_options_decision, pattern='^options_'),
                CallbackQueryHandler(option_selected, pattern='^option_')
            ],
            INPUT_COMPLEXITY: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_complexity)
            ]
        },
        fallbacks=[
            CommandHandler('cancel', cancel),
            CommandHandler('start', start)
        ]
    )
    
    # Добавляем обработчики
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('quick', quick_calculation))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(CallbackQueryHandler(new_calculation, pattern='^new_calculation$'))
    
    # Запускаем бота
    print("Бот запущен...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == '__main__':
    main()