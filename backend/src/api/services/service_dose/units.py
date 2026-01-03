from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, Optional, Tuple, Any


class UnitError(ValueError):
    pass

@dataclass(frozen=True)
class Unit:
    code: str
    kind: str
    base_code: Optional[str]
    to_base_factor: Optional[Decimal]

def _to_decimal(x: Any) -> Decimal:
    try:
        return x if isinstance(x, Decimal) else Decimal(str(x))
    except (InvalidOperation, TypeError):
        raise UnitError(f"Valeur numerique invalide: {x}")
    
def normalize_unit_code(u: str) -> str:
    if u is None:
        raise ValueError("Unite manquante")
    u = str(u).strip()
    if not u:
        raise UnitError("Unité vide.")

    u = u.replace("µ", "mc").replace("μ", "mc")  
    u = u.replace(" ", "")

    
    lower = u.lower()
    mapping = {
        "ml": "mL",
        "l": "L",
        "mg": "mg",
        "g": "g",
        "kg": "kg",
        "mcg": "mcg",
        "ug": "mcg",
        "ui": "UI",
        "iu": "UI",
        "h": "h",
        "hr": "h",
        "min": "min",
        "mn": "min",
        "s": "s",
        "sec": "s",
    }
    return mapping.get(lower, u)


def is_compound_unit(u: str) -> bool:
    return "/" in u


def split_compound_unit(u: str) -> Tuple[str, str]:
    """
    "mg/mL" -> ("mg", "mL")
    """
    u = normalize_unit_code(u)
    if "/" not in u:
        raise UnitError(f"Unité non composée: {u}")
    parts = u.split("/")
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise UnitError(f"Unité composée invalide: {u}")
    return normalize_unit_code(parts[0]), normalize_unit_code(parts[1])


class UnitsService:
    """
    Service de conversion d'unités basé sur:
    - core.units (base_code, to_base_factor)
    - core.unit_conversions (facteurs directs de from_unit -> to_unit)
    """

    def __init__(self, conn):
        self.conn = conn
        self._units: Dict[str, Unit] = {}
        self._direct: Dict[Tuple[str, str], Decimal] = {}
        self._loaded = False

    # ---------- DB loading ----------

    def _fetchall(self, cur) -> list:
        rows = cur.fetchall()
        return rows or []

    def _row_get(self, row, key: str, idx: int):
        # support dict cursor ou tuple
        if isinstance(row, dict):
            return row.get(key)
        return row[idx]

    def load(self) -> None:
        """
        Charge en mémoire un petit cache des unités et conversions.
        Appelé automatiquement à la première conversion.
        """
        if self._loaded:
            return

        with self.conn.cursor() as cur:
            # core.units
            cur.execute("""
                SELECT code, kind, base_code, to_base_factor
                FROM core.units
            """)
            for r in self._fetchall(cur):
                code = normalize_unit_code(self._row_get(r, "code", 0))
                kind = self._row_get(r, "kind", 1)
                base_code = self._row_get(r, "base_code", 2)
                to_base_factor = self._row_get(r, "to_base_factor", 3)
                self._units[code] = Unit(
                    code=code,
                    kind=kind,
                    base_code=normalize_unit_code(base_code) if base_code else None,
                    to_base_factor=_to_decimal(to_base_factor) if to_base_factor is not None else None
                )

            cur.execute("""
                SELECT from_unit, to_unit, factor
                FROM core.unit_conversions
            """)
            for r in self._fetchall(cur):
                fu = normalize_unit_code(self._row_get(r, "from_unit", 0))
                tu = normalize_unit_code(self._row_get(r, "to_unit", 1))
                factor = _to_decimal(self._row_get(r, "factor", 2))
                self._direct[(fu, tu)] = factor

        self._loaded = True



    def _get_unit(self, code: str) -> Optional[Unit]:
        self.load()
        code = normalize_unit_code(code)
        return self._units.get(code)

    def _direct_factor(self, from_u: str, to_u: str) -> Optional[Decimal]:
        self.load()
        from_u = normalize_unit_code(from_u)
        to_u = normalize_unit_code(to_u)
        if from_u == to_u:
            return Decimal("1")
        return self._direct.get((from_u, to_u))

    def _factor_via_base(self, from_u: str, to_u: str) -> Optional[Decimal]:
        """
        Conversion via base_code de core.units:
        from -> base (via to_base_factor)
        base -> to (via 1/to_base_factor)
        """
        uf = self._get_unit(from_u)
        ut = self._get_unit(to_u)
        if not uf or not ut:
            return None

        # Doivent être du même "kind"
        if uf.kind != ut.kind:
            return None

        # Si pas de base, pas de conversion via base
        if not uf.base_code or not ut.base_code:
            return None
        if uf.base_code != ut.base_code:
            return None

        # from->base
        if uf.to_base_factor is None or ut.to_base_factor is None:
            return None

        
        return uf.to_base_factor / ut.to_base_factor

    def get_factor(self, from_unit: str, to_unit: str) -> Decimal:
        """
        Facteur multiplicatif: value * factor => converti vers to_unit
        """
        from_unit = normalize_unit_code(from_unit)
        to_unit = normalize_unit_code(to_unit)

        if from_unit == to_unit:
            return Decimal("1")

        # 1) direct table
        f = self._direct_factor(from_unit, to_unit)
        if f is not None:
            return f

        # 2) inverse direct
        inv = self._direct_factor(to_unit, from_unit)
        if inv is not None and inv != 0:
            return Decimal("1") / inv

        # 3) via base (core.units)
        f2 = self._factor_via_base(from_unit, to_unit)
        if f2 is not None:
            return f2

        raise UnitError(f"Conversion impossible: {from_unit} -> {to_unit}")

    # ---------- Public conversions ----------

    def convert(self, value: Any, from_unit: str, to_unit: str) -> Decimal:
        v = _to_decimal(value)
        factor = self.get_factor(from_unit, to_unit)
        return v * factor

    def convert_compound(self, value: Any, from_unit: str, to_unit: str) -> Decimal:
        """
        Convertit des unités composées du type A/B.
        Exemple: mg/mL -> g/L, mL/h -> L/h, mg/kg -> mcg/kg etc.
        """
        v = _to_decimal(value)
        fn, fd = split_compound_unit(from_unit)
        tn, td = split_compound_unit(to_unit)

        # (fn/fd) -> (tn/td)
        # v * (fn->tn) / (fd->td)
        num_factor = self.get_factor(fn, tn)
        den_factor = self.get_factor(fd, td)
        if den_factor == 0:
            raise UnitError("Conversion impossible (facteur dénominateur nul).")
        return v * (num_factor / den_factor)

    def to_absolute_dose(self, value: Any, unit: str, *, weight_kg: Optional[Any] = None) -> Tuple[Decimal, str]:
        """
        Transforme une dose dépendante du poids (ex mg/kg) en dose absolue (mg),
        si weight_kg est fourni.
        Retour: (valeur, unité)
        """
        u = normalize_unit_code(unit)
        v = _to_decimal(value)

        if "/" not in u:
            return v, u

        num, den = split_compound_unit(u)

        # Cas mg/kg -> mg (si poids)
        if normalize_unit_code(den).lower() in {"kg"}:
            if weight_kg is None:
                raise UnitError(f"Poids requis pour convertir {u} en dose absolue.")
            w = _to_decimal(weight_kg)
            if w <= 0:
                raise UnitError("weight_kg doit être > 0.")
            # v (mg/kg) * kg => mg
            return v * w, num

        # On ne “devine” pas les autres (ex mg/mL) => ce n’est pas une dose absolue
        return v, u

    def ensure_unit_exists(self, unit: str) -> None:
        """
        Check “pédagogique”: si l’unité n’est pas connue de core.units et qu’elle
        n’apparaît pas dans unit_conversions, on avertit tôt.
        """
        self.load()
        u = normalize_unit_code(unit)
        if is_compound_unit(u):
            n, d = split_compound_unit(u)
            self.ensure_unit_exists(n)
            self.ensure_unit_exists(d)
            return

        if u in self._units:
            return

        for (fu, tu) in self._direct.keys():
            if fu == u or tu == u:
                return

        raise UnitError(f"Unité inconnue dans la base: {u}")