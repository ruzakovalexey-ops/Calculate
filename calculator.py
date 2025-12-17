import math
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
from enum import Enum


class TankType(Enum):
    SINGLE = "single"
    INSULATED = "insulated"
    DOUBLE = "double"
    BOILER = "boiler"


class MaterialType(Enum):
    AISI304 = "304"
    AISI316 = "316"
    AISI430 = "430"


class PressureType(Enum):
    NONE = 1
    LOW = 2
    HIGH = 3


# Константы
DENSITY = 7900  # кг/м³

PRICES = {
    '304': 350,  # руб/кг
    '316': 650,  # руб/кг
    '430': 200,  # руб/кг
    '304_jacket': 400  # руб/кг для рубашки
}

SHEET_SIZES = {
    '1000x2000': {'width': 1.0, 'height': 2.0},  # м
    '1250x2500': {'width': 1.25, 'height': 2.5},  # м
    '1500x3000': {'width': 1.5, 'height': 3.0}   # м
}

HEIGHT_OPTIONS = [
    500, 625, 750, 833, 1000, 1250, 1500, 2000, 2250, 2500,
    3000, 3750, 4000, 4500, 5000, 5500, 6000, 9000, 10250
]


@dataclass
class TankGeometry:
    """Геометрические параметры емкости"""
    diameter: float  # м
    height: float    # м
    volume_m3: float  # м³


@dataclass
class MaterialItem:
    """Элемент материала"""
    name: str
    weight: float  # кг
    steel_type: str
    price_per_kg: float  # руб/кг
    cost: float  # руб


@dataclass
class AdditionalSheet:
    """Дополнительный лист нержавейки"""
    material: str  # '304' или '316'
    size: str      # ключ из SHEET_SIZES
    thickness: float  # мм
    quantity: int


@dataclass
class AdditionalOptions:
    """Дополнительное оборудование"""
    luk400: bool = False  # Люк круглый DN400
    luk500: bool = False  # Люк круглый DN500
    level: bool = False   # Уровнемер
    valve: bool = False   # Дисковый затвор до DN50
    custom_cost: float = 0.0  # Прочие комплектующие (руб)


@dataclass
class TankParams:
    """Параметры расчета емкости"""
    volume: float  # литры
    height: float  # мм
    thickness_cylinder: float  # мм
    thickness_top: float  # мм
    thickness_bottom: float  # мм
    angle_top: float  # градусы
    angle_bottom: float  # градусы
    material: str  # '304' или '316'
    tank_type: str  # 'single', 'insulated', 'double', 'boiler'
    pressure: int = 1  # 1, 2, 3 (только для котла)


class TankCalculator:
    """Калькулятор стоимости емкостей из нержавеющей стали"""
    
    def __init__(self):
        self.complexity_coefficient = 3.5
        self.additional_sheets: List[AdditionalSheet] = []
        self.options = AdditionalOptions()
        
    def calculate_geometry(self, params: TankParams) -> TankGeometry:
        """Расчет геометрических параметров"""
        volume_m3 = params.volume / 1000  # переводим литры в м³
        height_m = params.height / 1000   # переводим мм в м
        
        # Рассчитываем радиус из объема цилиндра
        # V = π * r² * h => r = √(V / (π * h))
        radius = math.sqrt(volume_m3 / (math.pi * height_m))
        diameter = radius * 2
        
        return TankGeometry(
            diameter=diameter,
            height=height_m,
            volume_m3=volume_m3
        )
    
    def calculate_cylinder_weight(self, diameter: float, height: float, thickness_mm: float) -> float:
        """Расчет веса цилиндра"""
        thickness_m = thickness_mm / 1000  # переводим мм в м
        area = math.pi * diameter * height  # м²
        return area * thickness_m * DENSITY  # кг
    
    def calculate_cone_weight(self, diameter: float, angle_deg: float, thickness_mm: float) -> float:
        """Расчет веса конуса"""
        if angle_deg <= 0 or angle_deg >= 180:
            angle_deg = 90
        
        half_angle_rad = math.radians(angle_deg / 2)
        radius = diameter / 2
        thickness_m = thickness_mm / 1000
        
        # Высота конуса
        height = radius / math.tan(half_angle_rad)
        # Длина образующей
        slant_height = radius / math.sin(half_angle_rad)
        # Площадь боковой поверхности
        area = math.pi * radius * slant_height
        
        return area * thickness_m * DENSITY
    
    def calculate_single_wall_tank(self, params: TankParams, geometry: TankGeometry) -> Tuple[List[MaterialItem], float, float]:
        """Расчет одностенной емкости"""
        materials = []
        
        # Цилиндр
        cylinder_weight = self.calculate_cylinder_weight(
            geometry.diameter, geometry.height, params.thickness_cylinder
        )
        cylinder_cost = cylinder_weight * PRICES[params.material]
        materials.append(MaterialItem(
            name="Цилиндр емкости",
            weight=cylinder_weight,
            steel_type=f"AISI {params.material}",
            price_per_kg=PRICES[params.material],
            cost=cylinder_cost
        ))
        
        # Верхний конус
        top_cone_weight = self.calculate_cone_weight(
            geometry.diameter, params.angle_top, params.thickness_top
        )
        top_cone_cost = top_cone_weight * PRICES[params.material]
        materials.append(MaterialItem(
            name="Верхний конус",
            weight=top_cone_weight,
            steel_type=f"AISI {params.material}",
            price_per_kg=PRICES[params.material],
            cost=top_cone_cost
        ))
        
        # Нижний конус
        bottom_cone_weight = self.calculate_cone_weight(
            geometry.diameter, params.angle_bottom, params.thickness_bottom
        )
        bottom_cone_cost = bottom_cone_weight * PRICES[params.material]
        materials.append(MaterialItem(
            name="Нижний конус",
            weight=bottom_cone_weight,
            steel_type=f"AISI {params.material}",
            price_per_kg=PRICES[params.material],
            cost=bottom_cone_cost
        ))
        
        total_weight = cylinder_weight + top_cone_weight + bottom_cone_weight
        total_cost = cylinder_cost + top_cone_cost + bottom_cone_cost
        
        return materials, total_cost, total_weight
    
    def calculate_insulated_tank(self, params: TankParams, geometry: TankGeometry) -> Tuple[List[MaterialItem], float, float]:
        """Расчет емкости с теплоизоляционным кожухом"""
        materials, base_cost, base_weight = self.calculate_single_wall_tank(params, geometry)
        
        # Теплоизоляционный кожух (+90 мм к диаметру)
        insulation_diameter = geometry.diameter + 0.090  # м
        insulation_length = math.pi * insulation_diameter  # м
        insulation_thickness = 1.5  # мм
        insulation_thickness_m = insulation_thickness / 1000
        
        insulation_weight = insulation_length * geometry.height * insulation_thickness_m * DENSITY
        insulation_cost = insulation_weight * PRICES['430']
        
        materials.append(MaterialItem(
            name="Теплоизоляционный кожух",
            weight=insulation_weight,
            steel_type="AISI 430",
            price_per_kg=PRICES['430'],
            cost=insulation_cost
        ))
        
        total_cost = base_cost + insulation_cost
        total_weight = base_weight + insulation_weight
        
        return materials, total_cost, total_weight
    
    def calculate_double_wall_tank(self, params: TankParams, geometry: TankGeometry) -> Tuple[List[MaterialItem], float, float]:
        """Расчет двухстенной емкости с рубашкой"""
        materials, base_cost, base_weight = self.calculate_single_wall_tank(params, geometry)
        
        # Рубашка (+40 мм к диаметру)
        jacket_diameter = geometry.diameter + 0.040  # м
        jacket_length = math.pi * jacket_diameter  # м
        jacket_height = geometry.height * 2/3  # м
        jacket_thickness = 2.0  # мм
        jacket_thickness_m = jacket_thickness / 1000
        
        # Цилиндрическая часть рубашки
        jacket_cylinder_weight = jacket_length * jacket_height * jacket_thickness_m * DENSITY
        jacket_cylinder_cost = jacket_cylinder_weight * PRICES['304_jacket']
        
        # Конус рубашки
        jacket_cone_weight = self.calculate_cone_weight(
            jacket_diameter, params.angle_bottom, jacket_thickness
        )
        jacket_cone_cost = jacket_cone_weight * PRICES['304_jacket']
        
        materials.extend([
            MaterialItem(
                name="Цилиндрическая часть рубашки",
                weight=jacket_cylinder_weight,
                steel_type="AISI 304 (рубашка)",
                price_per_kg=PRICES['304_jacket'],
                cost=jacket_cylinder_cost
            ),
            MaterialItem(
                name="Конус рубашки",
                weight=jacket_cone_weight,
                steel_type="AISI 304 (рубашка)",
                price_per_kg=PRICES['304_jacket'],
                cost=jacket_cone_cost
            )
        ])
        
        total_cost = base_cost + jacket_cylinder_cost + jacket_cone_cost
        total_weight = base_weight + jacket_cylinder_weight + jacket_cone_weight
        
        return materials, total_cost, total_weight
    
    def calculate_boiler(self, params: TankParams, geometry: TankGeometry) -> Tuple[List[MaterialItem], float, float]:
        """Расчет варочного котла"""
        # Корректируем толщины в зависимости от давления
        thickness_cylinder = params.thickness_cylinder
        thickness_bottom = params.thickness_bottom
        jacket_cone_thickness = 2.0
        
        if params.pressure == 3:  # Свыше 3 атм
            thickness_cylinder = 4
            thickness_bottom = 4
            jacket_cone_thickness = 2
        
        # Внутренняя емкость
        materials, base_cost, base_weight = self.calculate_single_wall_tank(params, geometry)
        
        # Рубашка котла (+40 мм к диаметру)
        jacket_diameter = geometry.diameter + 0.040
        jacket_length = math.pi * jacket_diameter
        jacket_height = geometry.height * 2/3
        jacket_thickness = 2.0
        jacket_thickness_m = jacket_thickness / 1000
        
        jacket_cylinder_weight = jacket_length * jacket_height * jacket_thickness_m * DENSITY
        jacket_cylinder_cost = jacket_cylinder_weight * PRICES['304']
        
        jacket_cone_weight = self.calculate_cone_weight(
            jacket_diameter, params.angle_bottom, jacket_cone_thickness
        )
        jacket_cone_cost = jacket_cone_weight * PRICES['304']
        
        # Теплоизоляционный кожух котла (+90 мм к диаметру)
        insulation_diameter = geometry.diameter + 0.090
        insulation_length = math.pi * insulation_diameter
        insulation_thickness = 1.5
        insulation_thickness_m = insulation_thickness / 1000
        
        insulation_weight = insulation_length * geometry.height * insulation_thickness_m * DENSITY
        insulation_cost = insulation_weight * PRICES['430']
        
        materials.extend([
            MaterialItem(
                name="Цилиндрическая часть рубашки котла",
                weight=jacket_cylinder_weight,
                steel_type="AISI 304",
                price_per_kg=PRICES['304'],
                cost=jacket_cylinder_cost
            ),
            MaterialItem(
                name="Нижний конус рубашки котла",
                weight=jacket_cone_weight,
                steel_type="AISI 304",
                price_per_kg=PRICES['304'],
                cost=jacket_cone_cost
            ),
            MaterialItem(
                name="Теплоизоляционный кожух котла",
                weight=insulation_weight,
                steel_type="AISI 430",
                price_per_kg=PRICES['430'],
                cost=insulation_cost
            )
        ])
        
        total_cost = base_cost + jacket_cylinder_cost + jacket_cone_cost + insulation_cost
        total_weight = base_weight + jacket_cylinder_weight + jacket_cone_weight + insulation_weight
        
        return materials, total_cost, total_weight
    
    def calculate_additional_sheets_cost(self) -> Tuple[List[MaterialItem], float]:
        """Расчет стоимости дополнительных листов"""
        materials = []
        total_cost = 0
        
        for sheet in self.additional_sheets:
            size = SHEET_SIZES[sheet.size]
            area = size['width'] * size['height']  # м²
            volume = area * (sheet.thickness / 1000)  # м³
            weight = volume * DENSITY  # кг
            sheet_weight = weight * sheet.quantity
            sheet_cost = sheet_weight * PRICES[sheet.material]
            
            materials.append(MaterialItem(
                name=f"Лист {sheet.size} {sheet.thickness}мм",
                weight=sheet_weight,
                steel_type=f"AISI {sheet.material}",
                price_per_kg=PRICES[sheet.material],
                cost=sheet_cost
            ))
            
            total_cost += sheet_cost
        
        return materials, total_cost
    
    def calculate_options_cost(self) -> Tuple[List[MaterialItem], float]:
        """Расчет стоимости дополнительного оборудования"""
        materials = []
        total_cost = 0
        
        if self.options.luk400:
            cost = 30000
            materials.append(MaterialItem(
                name="Люк круглый DN400",
                weight=0,
                steel_type="",
                price_per_kg=0,
                cost=cost
            ))
            total_cost += cost
        
        if self.options.luk500:
            cost = 40000
            materials.append(MaterialItem(
                name="Люк круглый DN500",
                weight=0,
                steel_type="",
                price_per_kg=0,
                cost=cost
            ))
            total_cost += cost
        
        if self.options.level:
            cost = 12000
            materials.append(MaterialItem(
                name="Уровнемер",
                weight=0,
                steel_type="",
                price_per_kg=0,
                cost=cost
            ))
            total_cost += cost
        
        if self.options.valve:
            cost = 6000
            materials.append(MaterialItem(
                name="Дисковый затвор до DN50",
                weight=0,
                steel_type="",
                price_per_kg=0,
                cost=cost
            ))
            total_cost += cost
        
        if self.options.custom_cost > 0:
            materials.append(MaterialItem(
                name="Прочие комплектующие",
                weight=0,
                steel_type="",
                price_per_kg=0,
                cost=self.options.custom_cost
            ))
            total_cost += self.options.custom_cost
        
        return materials, total_cost
    
    def calculate(self, params: TankParams) -> Dict:
        """Основная функция расчета"""
        # Расчет геометрии
        geometry = self.calculate_geometry(params)
        
        # Расчет емкости в зависимости от типа
        if params.tank_type == 'single':
            materials, tank_cost, total_weight = self.calculate_single_wall_tank(params, geometry)
        elif params.tank_type == 'insulated':
            materials, tank_cost, total_weight = self.calculate_insulated_tank(params, geometry)
        elif params.tank_type == 'double':
            materials, tank_cost, total_weight = self.calculate_double_wall_tank(params, geometry)
        elif params.tank_type == 'boiler':
            materials, tank_cost, total_weight = self.calculate_boiler(params, geometry)
        else:
            raise ValueError(f"Неизвестный тип емкости: {params.tank_type}")
        
        # Расчет дополнительных листов
        sheet_materials, sheets_cost = self.calculate_additional_sheets_cost()
        
        # Расчет дополнительных опций
        option_materials, options_cost = self.calculate_options_cost()
        
        # Общая стоимость материалов (емкость + листы)
        total_material_cost = tank_cost + sheets_cost
        
        # Стоимость с коэффициентом сложности
        cost_with_complexity = total_material_cost * self.complexity_coefficient
        
        # Стоимость опций с коэффициентом 2.5
        options_cost_multiplied = options_cost * 2.5
        
        # Итоговая стоимость
        final_cost = cost_with_complexity + options_cost_multiplied
        
        return {
            'geometry': geometry,
            'materials': materials,
            'sheet_materials': sheet_materials,
            'option_materials': option_materials,
            'tank_cost': tank_cost,
            'sheets_cost': sheets_cost,
            'options_cost': options_cost,
            'total_weight': total_weight,
            'total_material_cost': total_material_cost,
            'cost_with_complexity': cost_with_complexity,
            'options_cost_multiplied': options_cost_multiplied,
            'final_cost': final_cost,
            'complexity': self.complexity_coefficient
        }