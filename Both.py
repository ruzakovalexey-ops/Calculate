import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ConversationHandler
import math

# Логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
DENSITY = 7900  # кг/м³
PRICES = {'304': 350, '316': 650, '430': 200, '304_jacket': 400}

# Состояния для ConversationHandler
(TYPE, VOLUME, HEIGHT, THICKNESS, ANGLES, MATERIAL, 
 ADD_SHEETS, ADD_OPTIONS, COMPLEXITY, CALCULATE) = range(10)

class TankCalculator:
    def __init__(self):
        self.user_data = {}
    
    def calculate_geometry(self, volume, height):
        """Расчет геометрических параметров"""
        volume_m3 = volume / 1000
        height_m = height / 1000
        radius = math.sqrt(volume_m3 / (math.pi * height_m))
        return {
            'diameter': radius * 2,
            'height': height_m,
            'volume_m3': volume_m3
        }
    
    def calculate_cylinder_weight(self, diameter, height, thickness):
        """Расчет веса цилиндра"""
        thickness_m = thickness / 1000
        area = math.pi * diameter * height
        return area * thickness_m * DENSITY
    
    def calculate_cone_weight(self, diameter, angle, thickness):
        """Расчет веса конуса"""
        if angle <= 0 or angle >= 180:
            angle = 90
        half_angle = math.radians(angle / 2)
        radius = diameter / 2
        thickness_m = thickness / 1000
        height = radius / math.tan(half_angle)
        slant_height = radius / math.sin(half_angle)
        area = math.pi * radius * slant_height
        return area * thickness_m * DENSITY
    
    def calculate_cost(self, user_data):
        """Основной расчет стоимости"""
        # Получаем параметры
        volume = user_data.get('volume', 1000)
        height = user_data.get('height', 1000)
        thickness_cyl = user_data.get('thickness_cyl', 3)
        thickness_top = user_data.get('thickness_top', 3)
        thickness_bottom = user_data.get('thickness_bottom', 4)
        angle_top = user_data.get('angle_top', 90)
        angle_bottom = user_data.get('angle_bottom', 90)
        material = user_data.get('material', '304')
        tank_type = user_data.get('tank_type', 'single')
        
        # Расчет геометрии
        geometry = self.calculate_geometry(volume, height)
        
        # Расчет весов
        cylinder_weight = self.calculate_cylinder_weight(
            geometry['diameter'], geometry['height'], thickness_cyl
        )
        top_cone_weight = self.calculate_cone_weight(
            geometry['diameter'], angle_top, thickness_top
        )
        bottom_cone_weight = self.calculate_cone_weight(
            geometry['diameter'], angle_bottom, thickness_bottom
        )
        
        # Расчет стоимости
        total_weight = cylinder_weight + top_cone_weight + bottom_cone_weight
        material_cost = total_weight * PRICES[material]
        
        # Коэффициент сложности
        complexity = user_data.get('complexity', 3.5)
        cost_with_complexity = material_cost * complexity
        
        # Дополнительные опции
        options_cost = 0
        options = user_data.get('options', {})
        if options.get('luk400'):
            options_cost += 30000
        if options.get('luk500'):
            options_cost += 40000
        if options.get('level'):
            options_cost += 12000
        if options.get('valve'):
            options_cost += 6000
        
        total_cost = cost_with_complexity + (options_cost * 2.5)
        
        return {
            'geometry': geometry,
            'weights': {
                'cylinder': cylinder_weight,
                'top_cone': top_cone_weight,
                'bottom_cone': bottom_cone_weight,
                'total': total_weight
            },
            'costs': {
                'material': material_cost,
                'with_complexity': cost_with_complexity,
                'options': options_cost,
                'options_x2_5': options_cost * 2.5,
                'total': total_cost
            },
            'parameters': {
                'diameter_mm': geometry['diameter'] * 1000,
                'height_mm': height,
                'volume': volume
            }
        }

calculator = TankCalculator()

async def start(update: Update, context):
    """Начало работы с ботом"""
    await update.message.reply_text(
        "🔧 *Калькулятор стоимости емкостей из нержавеющей стали*\n\n"
        "Выберите тип емкости:",
        parse_mode='Markdown',
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Одностенная", callback_data='single')],
            [InlineKeyboardButton("С теплоизоляционным кожухом", callback_data='insulated')],
            [InlineKeyboardButton("С рубашкой", callback_data='double')],
            [InlineKeyboardButton("Котел", callback_data='boiler')]
        ])
    )
    return TYPE

async def tank_type_selected(update: Update, context):
    """Обработка выбора типа емкости"""
    query = update.callback_query
    await query.answer()
    
    tank_type = query.data
    context.user_data['tank_type'] = tank_type
    
    await query.edit_message_text(
        f"Выбран тип: {get_tank_type_name(tank_type)}\n\n"
        "Введите объем емкости в литрах (например: 1000):"
    )
    return VOLUME

async def volume_entered(update: Update, context):
    """Обработка ввода объема"""
    try:
        volume = float(update.message.text)
        if volume <= 0:
            await update.message.reply_text("Объем должен быть положительным. Попробуйте снова:")
            return VOLUME
        
        context.user_data['volume'] = volume
        
        await update.message.reply_text(
            "Введите высоту цилиндра в мм (доступные варианты):\n"
            "500, 625, 750, 833, 1000, 1250, 1500, 2000, 2250, 2500, 3000, 3750, 4000, 4500, 5000, 5500, 6000, 9000, 10250"
        )
        return HEIGHT
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число:")
        return VOLUME

async def height_entered(update: Update, context):
    """Обработка ввода высоты"""
    try:
        height = float(update.message.text)
        context.user_data['height'] = height
        
        await update.message.reply_text(
            "Введите толщины стенок в мм через пробел:\n"
            "Цилиндр Верхний_конус Нижний_конус\n"
            "Например: 3 3 4"
        )
        return THICKNESS
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число:")
        return HEIGHT

async def thickness_entered(update: Update, context):
    """Обработка ввода толщин"""
    try:
        parts = update.message.text.split()
        if len(parts) != 3:
            await update.message.reply_text("Введите 3 числа через пробел:")
            return THICKNESS
        
        thickness_cyl = float(parts[0])
        thickness_top = float(parts[1])
        thickness_bottom = float(parts[2])
        
        context.user_data['thickness_cyl'] = thickness_cyl
        context.user_data['thickness_top'] = thickness_top
        context.user_data['thickness_bottom'] = thickness_bottom
        
        await update.message.reply_text(
            "Введите углы конусов в градусах через пробел:\n"
            "Верхний_конус Нижний_конус\n"
            "Например: 90 90"
        )
        return ANGLES
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числа:")
        return THICKNESS

async def angles_entered(update: Update, context):
    """Обработка ввода углов"""
    try:
        parts = update.message.text.split()
        if len(parts) != 2:
            await update.message.reply_text("Введите 2 числа через пробел:")
            return ANGLES
        
        angle_top = float(parts[0])
        angle_bottom = float(parts[1])
        
        context.user_data['angle_top'] = angle_top
        context.user_data['angle_bottom'] = angle_bottom
        
        await update.message.reply_text(
            "Выберите материал:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("AISI 304 (350 руб/кг)", callback_data='304')],
                [InlineKeyboardButton("AISI 316 (650 руб/кг)", callback_data='316')]
            ])
        )
        return MATERIAL
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите числа:")
        return ANGLES

async def material_selected(update: Update, context):
    """Обработка выбора материала"""
    query = update.callback_query
    await query.answer()
    
    material = query.data
    context.user_data['material'] = material
    
    await query.edit_message_text(
        f"Выбран материал: AISI {material}\n\n"
        "Введите коэффициент сложности (от 1 до 10, обычно 3.5):"
    )
    return COMPLEXITY

async def complexity_entered(update: Update, context):
    """Обработка ввода коэффициента сложности"""
    try:
        complexity = float(update.message.text)
        if complexity < 1 or complexity > 10:
            await update.message.reply_text("Коэффициент должен быть от 1 до 10:")
            return COMPLEXITY
        
        context.user_data['complexity'] = complexity
        
        await update.message.reply_text(
            "Выберите дополнительное оборудование (можно несколько):",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Люк DN400 (+30 000 руб)", callback_data='luk400')],
                [InlineKeyboardButton("Люк DN500 (+40 000 руб)", callback_data='luk500')],
                [InlineKeyboardButton("Уровнемер (+12 000 руб)", callback_data='level')],
                [InlineKeyboardButton("Затвор DN50 (+6 000 руб)", callback_data='valve')],
                [InlineKeyboardButton("Продолжить без опций", callback_data='continue')]
            ])
        )
        return ADD_OPTIONS
    except ValueError:
        await update.message.reply_text("Пожалуйста, введите число:")
        return COMPLEXITY

async def options_selected(update: Update, context):
    """Обработка выбора опций"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'continue':
        # Переходим к расчету
        return await calculate(update, context)
    
    # Инициализируем словарь опций
    if 'options' not in context.user_data:
        context.user_data['options'] = {}
    
    # Добавляем/убираем опцию
    option = query.data
    context.user_data['options'][option] = not context.user_data['options'].get(option, False)
    
    # Обновляем сообщение с текущим состоянием
    options_text = get_options_text(context.user_data.get('options', {}))
    
    await query.edit_message_text(
        f"Выбранные опции:\n{options_text}\n\n"
        "Выберите дополнительные опции или нажмите 'Продолжить':",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Люк DN400 (+30 000 руб)", callback_data='luk400')],
            [InlineKeyboardButton("Люк DN500 (+40 000 руб)", callback_data='luk500')],
            [InlineKeyboardButton("Уровнемер (+12 000 руб)", callback_data='level')],
            [InlineKeyboardButton("Затвор DN50 (+6 000 руб)", callback_data='valve')],
            [InlineKeyboardButton("Продолжить расчет", callback_data='continue')]
        ])
    )
    return ADD_OPTIONS

async def calculate(update: Update, context):
    """Выполнение расчета"""
    query = update.callback_query
    if query:
        await query.answer()
        message = query.message
    else:
        message = update.message
    
    # Выполняем расчет
    results = calculator.calculate_cost(context.user_data)
    
    # Формируем результат
    response = (
        f"📊 *Результаты расчета*\n\n"
        f"Тип емкости: {get_tank_type_name(context.user_data.get('tank_type'))}\n"
        f"Объем: {context.user_data.get('volume')} л\n"
        f"Высота: {context.user_data.get('height')} мм\n"
        f"Диаметр: {results['parameters']['diameter_mm']:.1f} мм\n\n"
        f"*Вес компонентов:*\n"
        f"Цилиндр: {results['weights']['cylinder']:.1f} кг\n"
        f"Верхний конус: {results['weights']['top_cone']:.1f} кг\n"
        f"Нижний конус: {results['weights']['bottom_cone']:.1f} кг\n"
        f"Общий вес: {results['weights']['total']:.1f} кг\n\n"
        f"*Стоимость:*\n"
        f"Материалы: {results['costs']['material']:,.0f} руб\n"
        f"Коэффициент сложности: {context.user_data.get('complexity', 3.5)}\n"
        f"Стоимость × коэф: {results['costs']['with_complexity']:,.0f} руб\n"
        f"Доп. оборудование: {results['costs']['options']:,.0f} руб\n"
        f"Доп. оборудование ×2.5: {results['costs']['options_x2_5']:,.0f} руб\n\n"
        f"💰 *ИТОГО: {results['costs']['total']:,.0f} руб*\n\n"
        f"Для нового расчета введите /start"
    )
    
    if query:
        await query.edit_message_text(response, parse_mode='Markdown')
    else:
        await message.reply_text(response, parse_mode='Markdown')
    
    return ConversationHandler.END

async def cancel(update: Update, context):
    """Отмена диалога"""
    await update.message.reply_text("Расчет отменен. Для нового расчета введите /start")
    return ConversationHandler.END

def get_tank_type_name(tank_type):
    """Получение названия типа емкости"""
    types = {
        'single': 'Одностенная',
        'insulated': 'С теплоизоляционным кожухом',
        'double': 'С рубашкой',
        'boiler': 'Котел'
    }
    return types.get(tank_type, 'Неизвестный тип')

def get_options_text(options):
    """Формирование текста выбранных опций"""
    if not options:
        return "Нет выбранных опций"
    
    texts = []
    if options.get('luk400'):
        texts.append("✓ Люк DN400")
    if options.get('luk500'):
        texts.append("✓ Люк DN500")
    if options.get('level'):
        texts.append("✓ Уровнемер")
    if options.get('valve'):
        texts.append("✓ Затвор DN50")
    
    return "\n".join(texts)

def main():
    """Запуск бота"""
    # Токен вашего бота (замените на реальный)
    TOKEN ="8206909527:AAHiduRetGDYMaL_H5v27jA6G1aTrUL_Jso"
    
    application = Application.builder().token(TOKEN).build()
    
    # Настройка ConversationHandler
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            TYPE: [CallbackQueryHandler(tank_type_selected)],
            VOLUME: [MessageHandler(filters.TEXT & ~filters.COMMAND, volume_entered)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, height_entered)],
            THICKNESS: [MessageHandler(filters.TEXT & ~filters.COMMAND, thickness_entered)],
            ANGLES: [MessageHandler(filters.TEXT & ~filters.COMMAND, angles_entered)],
            MATERIAL: [CallbackQueryHandler(material_selected)],
            COMPLEXITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, complexity_entered)],
            ADD_OPTIONS: [CallbackQueryHandler(options_selected)],
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('calculate', calculate))
    
    # Запуск бота
    application.run_polling()

if __name__ == '__main__':
    main()
