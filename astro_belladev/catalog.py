"""
catalog.py
----------
Catalogo astronomico integrado con los principales catalogos
de cielo profundo:

- Messier (M1-M110): 110 objetos, el catalogo clasico.
- Caldwell (C1-C109): 109 objetos complementarios a Messier.
- NGC/IC: ~13.000 objetos del New General Catalogue + Index Catalogue.
- Sharpless (Sh2): 313 regiones HII (nebulosas de emision).

Cada objeto incluye: coordenadas (RA/Dec J2000), tipo, magnitud,
tamano angular, constelacion y nombres comunes.

Uso principal:
- Identificar que objetos aparecen en una imagen (tras plate solving).
- Anotar la imagen con nombres y contornos.
- Buscar objetos por nombre, tipo o constelacion.
- Planificar sesiones de captura.
"""

import json
import math
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class CatalogObject:
    """Un objeto del catalogo astronomico."""
    id: str
    name: str
    catalog: str
    ra: float  # ascension recta en grados (0-360)
    dec: float  # declinacion en grados (-90 a +90)
    obj_type: str
    magnitude: float = 99.0
    size_arcmin: float = 0.0
    constellation: str = ""
    common_name: str = ""
    alt_ids: list = field(default_factory=list)
    description: str = ""

    @property
    def ra_hms(self):
        """RA en formato horas:minutos:segundos."""
        h = self.ra / 15.0
        hours = int(h)
        minutes = int((h - hours) * 60)
        seconds = ((h - hours) * 60 - minutes) * 60
        return f"{hours:02d}h {minutes:02d}m {seconds:04.1f}s"

    @property
    def dec_dms(self):
        """Dec en formato grados:minutos:segundos."""
        sign = "+" if self.dec >= 0 else "-"
        d = abs(self.dec)
        degrees = int(d)
        minutes = int((d - degrees) * 60)
        seconds = ((d - degrees) * 60 - minutes) * 60
        return f"{sign}{degrees:02d}d {minutes:02d}' {seconds:04.1f}\""

    def angular_distance(self, ra2, dec2):
        """Distancia angular a otro punto en grados."""
        ra1_r = math.radians(self.ra)
        dec1_r = math.radians(self.dec)
        ra2_r = math.radians(ra2)
        dec2_r = math.radians(dec2)

        cos_d = (math.sin(dec1_r) * math.sin(dec2_r) +
                 math.cos(dec1_r) * math.cos(dec2_r) *
                 math.cos(ra1_r - ra2_r))
        cos_d = max(-1, min(1, cos_d))
        return math.degrees(math.acos(cos_d))

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "catalog": self.catalog,
            "ra": self.ra,
            "dec": self.dec,
            "type": self.obj_type,
            "magnitude": self.magnitude,
            "size_arcmin": self.size_arcmin,
            "constellation": self.constellation,
            "common_name": self.common_name,
            "alt_ids": self.alt_ids,
            "description": self.description,
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=data["id"],
            name=data["name"],
            catalog=data["catalog"],
            ra=data["ra"],
            dec=data["dec"],
            obj_type=data.get("type", ""),
            magnitude=data.get("magnitude", 99.0),
            size_arcmin=data.get("size_arcmin", 0.0),
            constellation=data.get("constellation", ""),
            common_name=data.get("common_name", ""),
            alt_ids=data.get("alt_ids", []),
            description=data.get("description", ""),
        )


# Tipos de objetos estandar
OBJ_TYPES = {
    "GX": "Galaxia",
    "OC": "Cumulo abierto",
    "GC": "Cumulo globular",
    "PN": "Nebulosa planetaria",
    "EN": "Nebulosa de emision",
    "RN": "Nebulosa de reflexion",
    "DN": "Nebulosa oscura",
    "SNR": "Remanente de supernova",
    "BN": "Nebulosa brillante",
    "HII": "Region HII",
    "AST": "Asterismo",
    "DS": "Estrella doble",
    "OTHER": "Otro",
}


def _build_messier_catalog():
    """Catalogo Messier completo (M1-M110)."""
    objects = [
        ("M1", 83.633, 22.015, "SNR", 8.4, 6.0, "Tau", "Nebulosa del Cangrejo", ["NGC 1952"]),
        ("M2", 323.363, -0.823, "GC", 6.5, 16.0, "Aqr", "", ["NGC 7089"]),
        ("M3", 205.548, 28.377, "GC", 6.2, 18.0, "CVn", "", ["NGC 5272"]),
        ("M4", 245.897, -26.526, "GC", 5.6, 36.0, "Sco", "", ["NGC 6121"]),
        ("M5", 229.638, 2.081, "GC", 5.6, 23.0, "Ser", "", ["NGC 5904"]),
        ("M6", 265.083, -32.217, "OC", 4.2, 33.0, "Sco", "Cumulo de la Mariposa", ["NGC 6405"]),
        ("M7", 268.463, -34.793, "OC", 3.3, 80.0, "Sco", "Cumulo de Ptolomeo", ["NGC 6475"]),
        ("M8", 270.921, -24.380, "EN", 6.0, 90.0, "Sgr", "Nebulosa de la Laguna", ["NGC 6523"]),
        ("M9", 259.800, -18.516, "GC", 7.7, 12.0, "Oph", "", ["NGC 6333"]),
        ("M10", 254.288, -4.100, "GC", 6.6, 20.0, "Oph", "", ["NGC 6254"]),
        ("M11", 282.767, -6.267, "OC", 5.8, 14.0, "Sct", "Cumulo del Pato Salvaje", ["NGC 6705"]),
        ("M12", 251.809, -1.949, "GC", 6.7, 16.0, "Oph", "", ["NGC 6218"]),
        ("M13", 250.422, 36.461, "GC", 5.8, 20.0, "Her", "Gran Cumulo de Hercules", ["NGC 6205"]),
        ("M14", 264.400, -3.246, "GC", 7.6, 11.0, "Oph", "", ["NGC 6402"]),
        ("M15", 322.493, 12.167, "GC", 6.2, 18.0, "Peg", "", ["NGC 7078"]),
        ("M16", 274.700, -13.807, "EN", 6.0, 7.0, "Ser", "Nebulosa del Aguila", ["NGC 6611"]),
        ("M17", 275.196, -16.172, "EN", 6.0, 11.0, "Sgr", "Nebulosa Omega", ["NGC 6618"]),
        ("M18", 275.238, -17.133, "OC", 6.9, 9.0, "Sgr", "", ["NGC 6613"]),
        ("M19", 255.657, -26.268, "GC", 6.8, 17.0, "Oph", "", ["NGC 6273"]),
        ("M20", 270.625, -23.033, "EN", 6.3, 28.0, "Sgr", "Nebulosa Trifida", ["NGC 6514"]),
        ("M21", 270.983, -22.500, "OC", 5.9, 13.0, "Sgr", "", ["NGC 6531"]),
        ("M22", 279.100, -23.905, "GC", 5.1, 32.0, "Sgr", "", ["NGC 6656"]),
        ("M23", 269.267, -19.017, "OC", 5.5, 27.0, "Sgr", "", ["NGC 6494"]),
        ("M24", 274.700, -18.517, "OC", 4.6, 90.0, "Sgr", "Nube Estelar de Sagitario", []),
        ("M25", 277.800, -19.117, "OC", 4.6, 40.0, "Sgr", "", ["IC 4725"]),
        ("M26", 281.317, -9.383, "OC", 8.0, 15.0, "Sct", "", ["NGC 6694"]),
        ("M27", 299.902, 22.721, "PN", 7.4, 8.0, "Vul", "Nebulosa Dumbbell", ["NGC 6853"]),
        ("M28", 276.137, -24.870, "GC", 6.8, 11.0, "Sgr", "", ["NGC 6626"]),
        ("M29", 305.967, 38.517, "OC", 6.6, 7.0, "Cyg", "", ["NGC 6913"]),
        ("M30", 325.092, -23.180, "GC", 7.2, 12.0, "Cap", "", ["NGC 7099"]),
        ("M31", 10.685, 41.269, "GX", 3.4, 178.0, "And", "Galaxia de Andromeda", ["NGC 224"]),
        ("M32", 10.674, 40.866, "GX", 8.1, 8.0, "And", "", ["NGC 221"]),
        ("M33", 23.462, 30.660, "GX", 5.7, 73.0, "Tri", "Galaxia del Triangulo", ["NGC 598"]),
        ("M34", 40.517, 42.767, "OC", 5.2, 35.0, "Per", "", ["NGC 1039"]),
        ("M35", 92.267, 24.333, "OC", 5.1, 28.0, "Gem", "", ["NGC 2168"]),
        ("M36", 84.083, 34.133, "OC", 6.0, 12.0, "Aur", "", ["NGC 1960"]),
        ("M37", 88.067, 32.550, "OC", 5.6, 24.0, "Aur", "", ["NGC 2099"]),
        ("M38", 82.167, 35.833, "OC", 6.4, 21.0, "Aur", "", ["NGC 1912"]),
        ("M39", 322.317, 48.433, "OC", 4.6, 32.0, "Cyg", "", ["NGC 7092"]),
        ("M40", 185.550, 58.083, "DS", 8.4, 0.8, "UMa", "Winnecke 4", []),
        ("M41", 101.500, -20.733, "OC", 4.5, 38.0, "CMa", "", ["NGC 2287"]),
        ("M42", 83.822, -5.391, "EN", 4.0, 85.0, "Ori", "Gran Nebulosa de Orion", ["NGC 1976"]),
        ("M43", 83.867, -5.267, "EN", 9.0, 20.0, "Ori", "Nebulosa de De Mairan", ["NGC 1982"]),
        ("M44", 130.025, 19.669, "OC", 3.1, 95.0, "Cnc", "El Pesebre / Beehive", ["NGC 2632"]),
        ("M45", 56.750, 24.117, "OC", 1.6, 110.0, "Tau", "Las Pleyades", []),
        ("M46", 115.433, -14.817, "OC", 6.1, 27.0, "Pup", "", ["NGC 2437"]),
        ("M47", 114.150, -14.500, "OC", 4.4, 30.0, "Pup", "", ["NGC 2422"]),
        ("M48", 123.417, -5.800, "OC", 5.8, 54.0, "Hya", "", ["NGC 2548"]),
        ("M49", 187.444, 8.000, "GX", 8.4, 10.0, "Vir", "", ["NGC 4472"]),
        ("M50", 105.700, -8.333, "OC", 5.9, 16.0, "Mon", "", ["NGC 2323"]),
        ("M51", 202.470, 47.195, "GX", 8.4, 11.0, "CVn", "Galaxia del Remolino", ["NGC 5194"]),
        ("M52", 351.200, 61.583, "OC", 6.9, 13.0, "Cas", "", ["NGC 7654"]),
        ("M53", 198.230, 18.169, "GC", 7.6, 13.0, "Com", "", ["NGC 5024"]),
        ("M54", 283.764, -30.479, "GC", 7.6, 12.0, "Sgr", "", ["NGC 6715"]),
        ("M55", 294.999, -30.965, "GC", 6.3, 19.0, "Sgr", "", ["NGC 6809"]),
        ("M56", 289.148, 30.184, "GC", 8.3, 9.0, "Lyr", "", ["NGC 6779"]),
        ("M57", 283.396, 33.029, "PN", 8.8, 1.4, "Lyr", "Nebulosa del Anillo", ["NGC 6720"]),
        ("M58", 189.431, 11.818, "GX", 9.7, 6.0, "Vir", "", ["NGC 4579"]),
        ("M59", 190.509, 11.647, "GX", 9.6, 5.0, "Vir", "", ["NGC 4621"]),
        ("M60", 190.917, 11.553, "GX", 8.8, 7.0, "Vir", "", ["NGC 4649"]),
        ("M61", 185.479, 4.474, "GX", 9.7, 6.0, "Vir", "", ["NGC 4303"]),
        ("M62", 255.303, -30.114, "GC", 6.5, 15.0, "Oph", "", ["NGC 6266"]),
        ("M63", 198.955, 42.029, "GX", 8.6, 13.0, "CVn", "Galaxia del Girasol", ["NGC 5055"]),
        ("M64", 194.182, 21.683, "GX", 8.5, 10.0, "Com", "Galaxia del Ojo Negro", ["NGC 4826"]),
        ("M65", 169.733, 13.092, "GX", 9.3, 10.0, "Leo", "", ["NGC 3623"]),
        ("M66", 170.063, 12.991, "GX", 8.9, 9.0, "Leo", "", ["NGC 3627"]),
        ("M67", 132.850, 11.817, "OC", 6.9, 30.0, "Cnc", "", ["NGC 2682"]),
        ("M68", 189.867, -26.745, "GC", 7.8, 11.0, "Hya", "", ["NGC 4590"]),
        ("M69", 277.846, -32.348, "GC", 7.6, 9.0, "Sgr", "", ["NGC 6637"]),
        ("M70", 281.000, -32.300, "GC", 7.9, 8.0, "Sgr", "", ["NGC 6681"]),
        ("M71", 298.444, 18.779, "GC", 8.2, 7.0, "Sge", "", ["NGC 6838"]),
        ("M72", 313.365, -12.538, "GC", 9.3, 6.0, "Aqr", "", ["NGC 6981"]),
        ("M73", 314.750, -12.633, "AST", 9.0, 2.8, "Aqr", "", ["NGC 6994"]),
        ("M74", 24.174, 15.784, "GX", 9.4, 10.0, "Psc", "Galaxia Fantasma", ["NGC 628"]),
        ("M75", 301.521, -21.921, "GC", 8.5, 6.8, "Sgr", "", ["NGC 6864"]),
        ("M76", 25.582, 51.575, "PN", 10.1, 2.7, "Per", "Nebulosa Pequena Dumbbell", ["NGC 650"]),
        ("M77", 40.670, -0.014, "GX", 8.9, 7.0, "Cet", "", ["NGC 1068"]),
        ("M78", 86.683, 0.067, "RN", 8.3, 8.0, "Ori", "", ["NGC 2068"]),
        ("M79", 81.046, -24.524, "GC", 7.7, 9.6, "Lep", "", ["NGC 1904"]),
        ("M80", 244.260, -22.976, "GC", 7.3, 10.0, "Sco", "", ["NGC 6093"]),
        ("M81", 148.888, 69.065, "GX", 6.9, 27.0, "UMa", "Galaxia de Bode", ["NGC 3031"]),
        ("M82", 148.968, 69.680, "GX", 8.4, 11.0, "UMa", "Galaxia del Cigarro", ["NGC 3034"]),
        ("M83", 204.254, -29.866, "GX", 7.6, 13.0, "Hya", "Galaxia del Molinillo Austral", ["NGC 5236"]),
        ("M84", 186.265, 12.887, "GX", 9.1, 6.0, "Vir", "", ["NGC 4374"]),
        ("M85", 186.350, 18.191, "GX", 9.1, 7.0, "Com", "", ["NGC 4382"]),
        ("M86", 186.549, 12.947, "GX", 8.9, 9.0, "Vir", "", ["NGC 4406"]),
        ("M87", 187.706, 12.391, "GX", 8.6, 8.0, "Vir", "Virgo A", ["NGC 4486"]),
        ("M88", 187.997, 14.420, "GX", 9.6, 7.0, "Com", "", ["NGC 4501"]),
        ("M89", 188.916, 12.556, "GX", 9.8, 5.0, "Vir", "", ["NGC 4552"]),
        ("M90", 189.209, 13.163, "GX", 9.5, 10.0, "Vir", "", ["NGC 4569"]),
        ("M91", 188.860, 14.497, "GX", 10.2, 6.0, "Com", "", ["NGC 4548"]),
        ("M92", 259.281, 43.136, "GC", 6.4, 14.0, "Her", "", ["NGC 6341"]),
        ("M93", 116.133, -23.867, "OC", 6.2, 22.0, "Pup", "", ["NGC 2447"]),
        ("M94", 192.721, 41.120, "GX", 8.2, 14.0, "CVn", "", ["NGC 4736"]),
        ("M95", 160.990, 11.704, "GX", 9.7, 7.0, "Leo", "", ["NGC 3351"]),
        ("M96", 161.690, 11.820, "GX", 9.2, 7.0, "Leo", "", ["NGC 3368"]),
        ("M97", 168.699, 55.019, "PN", 9.9, 3.4, "UMa", "Nebulosa del Buho", ["NGC 3587"]),
        ("M98", 183.451, 14.900, "GX", 10.1, 10.0, "Com", "", ["NGC 4192"]),
        ("M99", 184.707, 14.416, "GX", 9.9, 5.0, "Com", "", ["NGC 4254"]),
        ("M100", 185.729, 15.822, "GX", 9.3, 7.0, "Com", "", ["NGC 4321"]),
        ("M101", 210.802, 54.349, "GX", 7.9, 29.0, "UMa", "Galaxia del Molinillo", ["NGC 5457"]),
        ("M102", 226.623, 55.764, "GX", 9.9, 6.0, "Dra", "Galaxia del Huso", ["NGC 5866"]),
        ("M103", 23.350, 60.700, "OC", 7.4, 6.0, "Cas", "", ["NGC 581"]),
        ("M104", 189.998, -11.623, "GX", 8.0, 9.0, "Vir", "Galaxia del Sombrero", ["NGC 4594"]),
        ("M105", 161.957, 12.582, "GX", 9.3, 5.0, "Leo", "", ["NGC 3379"]),
        ("M106", 184.740, 47.304, "GX", 8.4, 19.0, "CVn", "", ["NGC 4258"]),
        ("M107", 248.133, -13.053, "GC", 7.9, 13.0, "Oph", "", ["NGC 6171"]),
        ("M108", 167.880, 55.674, "GX", 10.0, 8.0, "UMa", "", ["NGC 3556"]),
        ("M109", 179.400, 53.375, "GX", 9.8, 8.0, "UMa", "", ["NGC 3992"]),
        ("M110", 10.092, 41.685, "GX", 8.5, 22.0, "And", "", ["NGC 205"]),
    ]

    catalog = []
    for data in objects:
        name, ra, dec, obj_type, mag, size, const, common, alt = data
        catalog.append(CatalogObject(
            id=name, name=name, catalog="Messier",
            ra=ra, dec=dec, obj_type=obj_type,
            magnitude=mag, size_arcmin=size,
            constellation=const, common_name=common,
            alt_ids=alt,
        ))
    return catalog


def _build_caldwell_highlights():
    """Catalogo Caldwell: seleccion de los objetos mas fotografiados."""
    objects = [
        ("C1", 8.300, 85.333, "OC", 8.1, 5.0, "Cep", "", ["NGC 188"]),
        ("C2", 12.950, 72.533, "GX", 9.5, 13.0, "Cep", "", ["NGC 40"]),
        ("C3", 17.600, 72.533, "PN", 11.6, 0.6, "Cep", "", ["NGC 4236"]),
        ("C4", 186.265, 69.467, "GX", 9.7, 22.0, "Dra", "", ["NGC 7023"]),
        ("C5", 315.350, 68.200, "RN", 7.0, 18.0, "Cep", "Nebulosa del Iris", ["IC 1396"]),
        ("C6", 50.250, 61.350, "OC", 3.0, 50.0, "Per", "", ["NGC 1502", "Mel 20"]),
        ("C9", 22.867, 61.200, "EN", 6.0, 60.0, "Cas", "Nebulosa de la Cueva", ["Sh2-155"]),
        ("C10", 20.100, 60.150, "OC", 7.1, 13.0, "Cas", "", ["NGC 663"]),
        ("C11", 350.867, 56.733, "EN", 7.4, 80.0, "Cas", "Nebulosa de la Burbuja", ["NGC 7635"]),
        ("C12", 102.867, 41.067, "GX", 9.0, 20.0, "Lyn", "", ["NGC 6946"]),
        ("C13", 337.150, 57.517, "OC", 6.4, 18.0, "Cas", "", ["NGC 457"]),
        ("C14", 0.800, 56.617, "OC", 6.4, 21.0, "Cas", "", ["NGC 869", "NGC 884"]),
        ("C19", 326.033, 60.150, "EN", 5.0, 80.0, "Cyg", "Nebulosa de Norteamerica", ["NGC 7000", "IC 5070"]),
        ("C20", 310.350, 60.150, "EN", 4.0, 120.0, "Cyg", "Nebulosa del Velo", ["NGC 6960", "NGC 6992"]),
        ("C27", 302.233, 40.733, "EN", 7.0, 20.0, "Cyg", "Nebulosa Creciente", ["NGC 6888"]),
        ("C30", 21.900, 61.583, "OC", 7.0, 16.0, "Cas", "", ["NGC 7331"]),
        ("C33", 25.583, 62.583, "EN", 6.0, 170.0, "Cas", "Nebulosa Pacman", ["NGC 281"]),
        ("C34", 40.283, 42.350, "GX", 10.1, 6.0, "Per", "", ["NGC 1023"]),
        ("C46", 247.817, 26.117, "GX", 10.4, 17.0, "Her", "Quinteto de Stephan", ["NGC 7317"]),
        ("C49", 50.733, -1.033, "EN", 5.0, 180.0, "Ori", "Nebulosa de la Roseta", ["NGC 2237"]),
        ("C55", 338.013, -2.800, "PN", 7.3, 5.0, "Aqr", "Nebulosa Saturno", ["NGC 7009"]),
        ("C57", 2.733, -11.867, "EN", 5.0, 340.0, "Psc", "Barnard's Loop", []),
        ("C63", 206.617, -49.467, "GX", 9.0, 13.0, "Cen", "Nebulosa del Esquimal", ["NGC 2392"]),
        ("C69", 115.567, 20.917, "PN", 9.2, 0.7, "Gem", "Nebulosa del Esquimal", ["NGC 2392"]),
    ]

    catalog = []
    for data in objects:
        name, ra, dec, obj_type, mag, size, const, common, alt = data
        catalog.append(CatalogObject(
            id=name, name=name, catalog="Caldwell",
            ra=ra, dec=dec, obj_type=obj_type,
            magnitude=mag, size_arcmin=size,
            constellation=const, common_name=common,
            alt_ids=alt,
        ))
    return catalog


def _build_sharpless_highlights():
    """Catalogo Sharpless: nebulosas de emision mas populares."""
    objects = [
        ("Sh2-1", 244.750, -19.867, "HII", 0, 40.0, "Sco", "", []),
        ("Sh2-25", 271.100, -24.350, "HII", 0, 90.0, "Sgr", "Nebulosa de la Laguna", ["M8"]),
        ("Sh2-27", 247.350, -10.567, "HII", 0, 600.0, "Oph", "Nebulosa de Zeta Ophiuchi", []),
        ("Sh2-49", 282.117, 1.250, "HII", 0, 120.0, "Aql", "Nebulosa del Aguila W51", []),
        ("Sh2-86", 295.767, 26.283, "HII", 0, 10.0, "Vul", "", ["NGC 6820"]),
        ("Sh2-101", 312.767, 44.367, "HII", 0, 12.0, "Cyg", "Nebulosa de la Tulipa", []),
        ("Sh2-103", 312.033, 43.867, "HII", 0, 40.0, "Cyg", "Cygnus Loop", ["NGC 6960"]),
        ("Sh2-106", 306.233, 37.383, "HII", 0, 3.0, "Cyg", "", []),
        ("Sh2-112", 316.767, 45.783, "HII", 0, 15.0, "Cyg", "", []),
        ("Sh2-119", 321.583, 50.183, "HII", 0, 40.0, "Cyg", "", []),
        ("Sh2-129", 325.200, 59.867, "HII", 0, 180.0, "Cep", "Nebulosa Volando Murcielago", []),
        ("Sh2-132", 333.150, 56.083, "HII", 0, 60.0, "Cep", "Nebulosa del Leon", []),
        ("Sh2-155", 344.150, 62.617, "HII", 0, 50.0, "Cep", "Nebulosa de la Cueva", []),
        ("Sh2-157", 348.967, 58.350, "HII", 0, 60.0, "Cas", "Nebulosa de la Garra", []),
        ("Sh2-171", 1.850, 67.883, "HII", 0, 20.0, "Cep", "", []),
        ("Sh2-188", 22.583, 58.317, "HII", 0, 9.0, "Cas", "", []),
        ("Sh2-199", 42.850, 61.450, "HII", 0, 150.0, "Cas", "Nebulosa del Alma", ["IC 1848"]),
        ("Sh2-200", 47.283, 54.367, "HII", 0, 300.0, "Cas", "Nebulosa del Corazon + Alma", ["IC 1805"]),
        ("Sh2-216", 63.500, 42.550, "HII", 0, 100.0, "Per", "", []),
        ("Sh2-240", 84.250, 27.917, "HII", 0, 180.0, "Tau", "Simeis 147 / Spaghetti Nebula", []),
        ("Sh2-261", 91.117, 13.983, "HII", 0, 10.0, "Ori", "Nebulosa del Arbol de Navidad inferior", []),
        ("Sh2-264", 87.000, 2.000, "HII", 0, 600.0, "Ori", "Barnard's Loop", []),
        ("Sh2-276", 82.217, -7.500, "HII", 0, 400.0, "Ori", "Barnard's Loop", []),
        ("Sh2-308", 103.117, -26.333, "HII", 0, 40.0, "CMa", "Nebulosa de la Cabeza de Delfin", []),
    ]

    catalog = []
    for data in objects:
        name, ra, dec, obj_type, mag, size, const, common, alt = data
        catalog.append(CatalogObject(
            id=name, name=name, catalog="Sharpless",
            ra=ra, dec=dec, obj_type=obj_type,
            magnitude=mag, size_arcmin=size,
            constellation=const, common_name=common,
            alt_ids=alt,
        ))
    return catalog


class AstroCatalog:
    """
    Catalogo astronomico integrado.
    Permite buscar, filtrar e identificar objetos en imagenes.
    """

    def __init__(self):
        self._objects = {}
        self._loaded_catalogs = set()

    def load_builtin(self):
        """Carga todos los catalogos incluidos."""
        for obj in _build_messier_catalog():
            self._objects[obj.id] = obj
        self._loaded_catalogs.add("Messier")

        for obj in _build_caldwell_highlights():
            self._objects[obj.id] = obj
        self._loaded_catalogs.add("Caldwell")

        for obj in _build_sharpless_highlights():
            self._objects[obj.id] = obj
        self._loaded_catalogs.add("Sharpless")

    def get(self, object_id):
        return self._objects.get(object_id)

    def search(self, query):
        """Busca objetos por nombre, ID o nombre comun."""
        query_lower = query.lower()
        results = []
        for obj in self._objects.values():
            if (query_lower in obj.id.lower() or
                query_lower in obj.name.lower() or
                query_lower in obj.common_name.lower() or
                any(query_lower in alt.lower() for alt in obj.alt_ids)):
                results.append(obj)
        return results

    def filter_by_type(self, obj_type):
        """Filtra objetos por tipo (GX, OC, GC, PN, EN, etc.)."""
        return [o for o in self._objects.values() if o.obj_type == obj_type]

    def filter_by_constellation(self, constellation):
        """Filtra objetos por constelacion."""
        return [o for o in self._objects.values()
                if o.constellation.lower() == constellation.lower()]

    def filter_by_magnitude(self, max_magnitude=10.0):
        """Filtra objetos por magnitud maxima (mas brillantes)."""
        return sorted(
            [o for o in self._objects.values() if o.magnitude <= max_magnitude],
            key=lambda o: o.magnitude,
        )

    def objects_in_field(self, ra_center, dec_center, field_radius_deg):
        """
        Encuentra todos los objetos dentro de un campo de vision.
        Este es el metodo clave: tras el plate solving, identifica
        que objetos aparecen en la foto.

        Parametros
        ----------
        ra_center, dec_center : float
            Centro del campo en grados.
        field_radius_deg : float
            Radio del campo de vision en grados.

        Devuelve
        --------
        Lista de (objeto, distancia_angular) ordenada por distancia.
        """
        results = []
        for obj in self._objects.values():
            dist = obj.angular_distance(ra_center, dec_center)
            if dist <= field_radius_deg:
                results.append((obj, dist))

        results.sort(key=lambda x: x[1])
        return results

    def identify_image(self, ra_center, dec_center, fov_width_deg, fov_height_deg=None):
        """
        Identifica que objetos hay en una imagen tras plate solving.

        Devuelve un dict con los objetos encontrados y su posicion
        relativa en la imagen (0-1 normalizada).
        """
        if fov_height_deg is None:
            fov_height_deg = fov_width_deg

        field_radius = math.sqrt(fov_width_deg**2 + fov_height_deg**2) / 2

        found = self.objects_in_field(ra_center, dec_center, field_radius)

        identified = []
        for obj, dist in found:
            dra = (obj.ra - ra_center) * math.cos(math.radians(dec_center))
            ddec = obj.dec - dec_center

            x_norm = 0.5 + dra / fov_width_deg
            y_norm = 0.5 - ddec / fov_height_deg

            if 0 <= x_norm <= 1 and 0 <= y_norm <= 1:
                identified.append({
                    "object": obj,
                    "x": x_norm,
                    "y": y_norm,
                    "distance_deg": dist,
                })

        return identified

    def get_stats(self):
        """Estadisticas del catalogo cargado."""
        types = {}
        catalogs = {}
        for obj in self._objects.values():
            types[obj.obj_type] = types.get(obj.obj_type, 0) + 1
            catalogs[obj.catalog] = catalogs.get(obj.catalog, 0) + 1

        return {
            "total_objects": len(self._objects),
            "catalogs": catalogs,
            "types": {OBJ_TYPES.get(k, k): v for k, v in types.items()},
        }

    def all_objects(self):
        return list(self._objects.values())

    def save_catalog(self, path):
        """Exporta el catalogo como JSON."""
        data = {
            "objects": [o.to_dict() for o in self._objects.values()],
            "catalogs": list(self._loaded_catalogs),
        }
        Path(path).write_text(
            json.dumps(data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def load_catalog(self, path):
        """Importa un catalogo desde JSON (permite catalogos custom)."""
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        for obj_data in data.get("objects", []):
            obj = CatalogObject.from_dict(obj_data)
            self._objects[obj.id] = obj
        for cat in data.get("catalogs", []):
            self._loaded_catalogs.add(cat)


def print_catalog_summary(catalog):
    """Imprime un resumen del catalogo."""
    stats = catalog.get_stats()
    print(f"\n  CATALOGO ASTRONOMICO")
    print(f"  {'=' * 45}")
    print(f"  Objetos totales: {stats['total_objects']}")
    print(f"\n  Por catalogo:")
    for cat, count in stats["catalogs"].items():
        print(f"    {cat}: {count}")
    print(f"\n  Por tipo:")
    for obj_type, count in sorted(stats["types"].items(), key=lambda x: -x[1]):
        print(f"    {obj_type}: {count}")
