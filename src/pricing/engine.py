from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal, Dict, Any

# Fixed default weight per square meter (can be overridden per request)
KG_PER_M2: float = 24.0

Origin = Literal["ES", "IT", "PT", "PL"]
Destination = Literal["GR-mainland", "GR-crete"]
PalletType = Literal["eu", "industrial"]
TransportMode = Literal["road", "groupage"]

@dataclass
class PricingRequest:
    buy_price_eur_m2: float
    qty_m2: float
    kg_per_m2: float
    pallets_count: int
    pallet_type: PalletType
    origin: Origin
    destination: Destination
    margin: float  # gross margin target, e.g., 0.40
    transport_mode: TransportMode = "road"
    freight_override_eur: float | None = None

class PricingEngine:
    def __init__(self, tariffs: Dict[str, Any]):
        self.tariffs = tariffs

    def calculate(self, r: PricingRequest) -> Dict[str, Any]:
        if r.qty_m2 <= 0:
            raise ValueError("qty_m2 must be > 0")
        if r.kg_per_m2 <= 0:
            raise ValueError("kg_per_m2 must be > 0")
        if not (0 < r.margin < 1):
            raise ValueError("margin must be between 0 and 1 (e.g., 0.40)")

        # 1) m² -> kg προϊόντος (kg/m² μπορεί να παραμετροποιηθεί)
        kg_tiles = r.qty_m2 * r.kg_per_m2

        # 2) Βάρος + κόστος παλέτας
        pconf = self.tariffs["pallets"][r.pallet_type]
        kg_total = kg_tiles + r.pallets_count * pconf["weight_kg"]
        pallet_cost = r.pallets_count * pconf["cost_eur"]

        # 3) Μεταφορικά ανά προέλευση/τρόπο
        freight = 0.0
        extras = 0.0
        extras_breakdown = []

        # Validate/adjust transport mode: Groupage επιτρέπεται μόνο για Ισπανία και Πολωνία
        mode = r.transport_mode or "road"
        if (r.origin not in ("ES", "PL")) and mode == "groupage":
            mode = "road"

        if r.origin == "ES":
            if mode == "groupage":
                freight = self._freight_groupage(kg_total)
                extras_breakdown.append({
                    "code": "groupage_mode",
                    "label": "Μεταφορικά Groupage (ES)",
                    "amount": round(freight, 2)
                })
            else:
                freight = self._freight_es(kg_total)
        elif r.origin == "IT":
            freight = self._freight_it(kg_total)
            # Extra για industrial παλέτα Ιταλίας
            if r.pallet_type == "industrial":
                it_extra = self.tariffs["it_extras"]["industrial_pallet_extra_eur"] * r.pallets_count
                extras += it_extra
                extras_breakdown.append({
                    "code": "it_industrial_pallet_extra",
                    "label": f"Επιβάρυνση Βιομηχανικής Παλέτας (IT) x{r.pallets_count}",
                    "amount": round(it_extra, 2)
                })
        elif r.origin == "PT":
            # Υποθέτουμε μεταφορικά σαν ES για απλότητα, προσαρμόστε αν διαφέρει
            freight = self._freight_es(kg_total)
            pt_extra = self.tariffs["pt_extras"]["surcharge_eur_per_m2"] * r.qty_m2
            extras += pt_extra
            extras_breakdown.append({
                "code": "pt_surcharge_per_m2",
                "label": f"Επιβάρυνση Πορτογαλίας ανά m² x{r.qty_m2}",
                "amount": round(pt_extra, 2)
            })
        elif r.origin == "PL":
            # Για Πολωνία, τα μεταφορικά είναι μεταβλητά και εισάγονται απευθείας από τον χρήστη
            if r.freight_override_eur is not None:
                freight = float(r.freight_override_eur)
                extras_breakdown.append({
                    "code": "pl_manual_freight",
                    "label": "Μεταφορικά Πολωνίας (χειροκίνητη εισαγωγή)",
                    "amount": round(freight, 2)
                })
            else:
                freight = 0.0
        else:
            raise ValueError("Unsupported origin")

        # 4) Extra Κρήτη ανά κιλό
        if r.destination == "GR-crete":
            crete_extra = kg_total * self.tariffs["gr_extras"]["crete_eur_per_kg"]
            extras += crete_extra
            extras_breakdown.append({
                "code": "gr_crete_island_surcharge",
                "label": f"Νησιωτική Επιβάρυνση Κρήτης ανά kg x{round(kg_total, 2)} kg",
                "amount": round(crete_extra, 2)
            })

        # 5) Συνολικό κόστος (χωρίς ΦΠΑ)
        cost_goods = r.buy_price_eur_m2 * r.qty_m2
        logistics = freight + extras + pallet_cost
        total_cost = cost_goods + logistics
        cost_per_m2 = total_cost / r.qty_m2

        # 6) Τιμή πώλησης με gross margin
        sell_price_per_m2 = cost_per_m2 / (1.0 - r.margin)

        # 7) KPIs
        markup_equiv = (sell_price_per_m2 / cost_per_m2) - 1.0

        return {
            "inputs": r.__dict__,
            "assumptions": {
                "kg_per_m2": r.kg_per_m2,
            },
            "weights": {
                "kg_tiles": round(kg_tiles, 2),
                "kg_total": round(kg_total, 2),
            },
            "cost": {
                "cost_goods": round(cost_goods, 2),
                "freight": round(freight, 2),
                "extras": round(extras, 2),
                "extras_breakdown": extras_breakdown,
                "pallet_cost": round(pallet_cost, 2),
                "logistics": round(logistics, 2),
                "total_cost": round(total_cost, 2),
                "cost_per_m2": round(cost_per_m2, 2),
            },
            "pricing": {
                "sell_price_per_m2": round(sell_price_per_m2, 2),
                "margin": r.margin,
                "markup_equiv": round(markup_equiv, 4),
            }
        }

    def _freight_es(self, kg: float) -> float:
        es = self.tariffs["es_freight"]
        for band in es["bands"]:
            if band["min_kg"] <= kg <= band["max_kg"]:
                return float(band.get("flat_eur", 0)) or kg * float(band.get("eur_per_kg", 0))
        return kg * float(es.get("default_eur_per_kg", 0))

    def _freight_it(self, kg: float) -> float:
        it = self.tariffs["it_freight"]
        for band in it["bands"]:
            if band["min_kg"] <= kg <= band["max_kg"]:
                return float(band.get("flat_eur", 0)) or kg * float(band.get("eur_per_kg", 0))
        return kg * float(it.get("default_eur_per_kg", 0))

    def _freight_groupage(self, kg: float) -> float:
        grp = self.tariffs["groupage"]
        # Tariff file structure: { "groupage": [ {min_kg, max_kg, flat_eur? , eur_per_kg?}, ... ] }
        bands = grp.get("groupage", []) if isinstance(grp, dict) else grp
        for band in bands:
            if band["min_kg"] <= kg <= band["max_kg"]:
                flat = float(band.get("flat_eur", 0))
                per = float(band.get("eur_per_kg", 0))
                return flat if flat > 0 else kg * per
        # If out of defined ranges, use last per-kg if available
        if bands:
            last = bands[-1]
            per = float(last.get("eur_per_kg", 0))
            return kg * per
        return 0.0


def load_tariffs(base_path: str) -> Dict[str, Any]:
    def read(name: str):
        with open(os.path.join(base_path, name), "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        **read("extras.json"),
        "es_freight": read("helios_es.json"),
        "it_freight": read("hermes_it.json"),
        "groupage": read("groupage.json"),
    }

def save_tariffs(new_tariffs: Dict[str, Any], base_path: str) -> None:
    # Αποθήκευση μόνο των τριών γνωστών segment σε ξεχωριστά αρχεία για καθαρότητα
    def write(name: str, data: Dict[str, Any]):
        with open(os.path.join(base_path, name), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    # Προσοχή στα κλειδιά που περιμένει το app
    write("extras.json", {
        "gr_extras": new_tariffs.get("gr_extras", {}),
        "pallets": new_tariffs.get("pallets", {}),
        "pt_extras": new_tariffs.get("pt_extras", {}),
        "it_extras": new_tariffs.get("it_extras", {})
    })
    write("helios_es.json", new_tariffs.get("es_freight", {}))
    write("hermes_it.json", new_tariffs.get("it_freight", {}))