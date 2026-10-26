"""
Battery Chemistry and Vehicle Pack Database
Defines physical aging parameters, nominal capacities, and voltage behaviors
for major electric vehicle battery chemistries and models.
"""

from dataclasses import dataclass
from typing import Dict, Optional, Tuple


@dataclass
class ChemistryProfile:
    name: str
    code: str
    nominal_cell_voltage: float
    flat_voltage_curve: bool
    typical_cycle_life_80: int
    knee_cycle_threshold: float
    calendar_knee_years: float
    dc_fast_charge_sensitivity: float
    optimal_temp_celsius: float
    activation_energy_kj: float
    recommended_target_soc: int
    description: str


CHEMISTRIES: Dict[str, ChemistryProfile] = {
    "LFP": ChemistryProfile(
        name="Lithium Iron Phosphate (LiFePO4)",
        code="LFP",
        nominal_cell_voltage=3.2,
        flat_voltage_curve=True,
        typical_cycle_life_80=3500,
        knee_cycle_threshold=2800.0,
        calendar_knee_years=12.0,
        dc_fast_charge_sensitivity=1.8,
        optimal_temp_celsius=20.0,
        activation_energy_kj=50.0,
        recommended_target_soc=100,
        description="Exceptional cycle life, highly flat voltage plateau requiring regular 100% calibration, excellent thermal runaway tolerance."
    ),
    "NMC": ChemistryProfile(
        name="Nickel Manganese Cobalt (NCM 622/811)",
        code="NMC",
        nominal_cell_voltage=3.65,
        flat_voltage_curve=False,
        typical_cycle_life_80=1500,
        knee_cycle_threshold=1400.0,
        calendar_knee_years=10.0,
        dc_fast_charge_sensitivity=2.4,
        optimal_temp_celsius=22.0,
        activation_energy_kj=55.0,
        recommended_target_soc=80,
        description="High energy density, sloping voltage curve allowing easy BMS tracking, sensitive to high SoC (>80%) storage and high temperature."
    ),
    "NCA": ChemistryProfile(
        name="Nickel Cobalt Aluminum Oxide (LiNiCoAlO2)",
        code="NCA",
        nominal_cell_voltage=3.6,
        flat_voltage_curve=False,
        typical_cycle_life_80=1200,
        knee_cycle_threshold=1100.0,
        calendar_knee_years=9.0,
        dc_fast_charge_sensitivity=2.6,
        optimal_temp_celsius=21.0,
        activation_energy_kj=58.0,
        recommended_target_soc=80,
        description="Very high energy density, sensitive to calendar aging at full charge, standard in older Tesla Model S/X and early Model 3 Performance."
    ),
    "SODIUM_ION": ChemistryProfile(
        name="Sodium-Ion (Na-Ion)",
        code="SODIUM_ION",
        nominal_cell_voltage=3.0,
        flat_voltage_curve=False,
        typical_cycle_life_80=2500,
        knee_cycle_threshold=2200.0,
        calendar_knee_years=11.0,
        dc_fast_charge_sensitivity=1.5,
        optimal_temp_celsius=20.0,
        activation_energy_kj=45.0,
        recommended_target_soc=100,
        description="Abundant materials, excellent cold-weather performance and thermal stability, moderate energy density."
    )
}


@dataclass
class VehiclePack:
    make: str
    model: str
    variant: str
    nominal_usable_kwh: float
    gross_kwh: float
    chemistry: ChemistryProfile
    wltp_range_km: int


VEHICLE_CATALOG: Dict[str, VehiclePack] = {
    # Tesla
    "tesla_model_y_rwd_lfp": VehiclePack(
        make="Tesla", model="Model Y", variant="RWD / Propulsion (CATL 60)",
        nominal_usable_kwh=59.6, gross_kwh=62.0, chemistry=CHEMISTRIES["LFP"], wltp_range_km=455
    ),
    "tesla_model_y_lr_nmc": VehiclePack(
        make="Tesla", model="Model Y", variant="Long Range AWD (LG 79)",
        nominal_usable_kwh=75.0, gross_kwh=79.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=533
    ),
    "tesla_model_3_rwd_lfp": VehiclePack(
        make="Tesla", model="Model 3", variant="RWD (CATL 60 / Highland)",
        nominal_usable_kwh=59.6, gross_kwh=62.0, chemistry=CHEMISTRIES["LFP"], wltp_range_km=513
    ),
    "tesla_model_3_lr_nmc": VehiclePack(
        make="Tesla", model="Model 3", variant="Long Range (LG/Panasonic 79)",
        nominal_usable_kwh=75.0, gross_kwh=82.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=629
    ),

    # Stellantis / Peugeot
    "peugeot_e208_50": VehiclePack(
        make="Peugeot", model="e-208", variant="50 kWh (CATL NMC)",
        nominal_usable_kwh=46.3, gross_kwh=50.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=362
    ),
    "peugeot_e208_54": VehiclePack(
        make="Peugeot", model="e-208", variant="54 kWh (Nidec/Emotors)",
        nominal_usable_kwh=48.1, gross_kwh=54.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=400
    ),

    # Renault
    "renault_zoe_52": VehiclePack(
        make="Renault", model="Zoe", variant="ZE50 (LG Chem)",
        nominal_usable_kwh=52.0, gross_kwh=54.7, chemistry=CHEMISTRIES["NMC"], wltp_range_km=395
    ),
    "renault_megane_ev60": VehiclePack(
        make="Renault", model="Megane E-Tech", variant="EV60 (LG NMC)",
        nominal_usable_kwh=60.0, gross_kwh=65.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=450
    ),

    # Volkswagen Group
    "vw_id3_pro_58": VehiclePack(
        make="Volkswagen", model="ID.3", variant="Pro Performance 58 kWh",
        nominal_usable_kwh=58.0, gross_kwh=62.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=425
    ),
    "vw_id4_pro_77": VehiclePack(
        make="Volkswagen", model="ID.4", variant="Pro 77 kWh (LG/CATL)",
        nominal_usable_kwh=77.0, gross_kwh=82.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=520
    ),

    # MG
    "mg_mg4_standard_lfp": VehiclePack(
        make="MG", model="MG4", variant="Standard (LFP 51 kWh)",
        nominal_usable_kwh=50.8, gross_kwh=51.0, chemistry=CHEMISTRIES["LFP"], wltp_range_km=350
    ),
    "mg_mg4_comfort_nmc": VehiclePack(
        make="MG", model="MG4", variant="Comfort / Luxury (NMC 64 kWh)",
        nominal_usable_kwh=61.7, gross_kwh=64.0, chemistry=CHEMISTRIES["NMC"], wltp_range_km=450
    ),

    # Hyundai / Kia (E-GMP)
    "hyundai_ioniq5_77": VehiclePack(
        make="Hyundai", model="Ioniq 5", variant="Long Range (SK On 77.4 kWh)",
        nominal_usable_kwh=74.0, gross_kwh=77.4, chemistry=CHEMISTRIES["NMC"], wltp_range_km=507
    ),
    "kia_ev6_77": VehiclePack(
        make="Kia", model="EV6", variant="Long Range (SK On 77.4 kWh)",
        nominal_usable_kwh=74.0, gross_kwh=77.4, chemistry=CHEMISTRIES["NMC"], wltp_range_km=528
    ),
}


def infer_pack_from_capacity(estimated_kwh: float) -> Tuple[str, VehiclePack]:
    """
    Finds the closest vehicle pack profile matching an estimated baseline capacity.
    """
    best_key = "tesla_model_y_rwd_lfp"
    best_diff = float("inf")

    for key, pack in VEHICLE_CATALOG.items():
        diff = abs(pack.nominal_usable_kwh - estimated_kwh)
        if diff < best_diff:
            best_diff = diff
            best_key = key

    return best_key, VEHICLE_CATALOG[best_key]
