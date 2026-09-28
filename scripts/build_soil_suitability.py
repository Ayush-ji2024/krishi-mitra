"""
Build the soil -> crop suitability table used by the API.

Why: the Kaggle crop dataset has no soil column, so the ML model cannot use soil
type. Instead we use an external, citable source - the FAO ECOCROP database -
which lists, for each crop, the soil TEXTURES it grows in:
    TEXT  = optimal textures        (e.g. "heavy, medium")
    TEXTR = absolute (tolerated)    (e.g. "heavy, medium, light")

Our 4 soil classes are mapped to textures (see SOIL_TEXTURE below), and each
crop gets a rating per soil:
    good     - the soil's texture is in the crop's OPTIMAL range
    possible - it is only in the crop's ABSOLUTE (tolerated) range
    poor     - it is in neither

Source data: FAO ECOCROP, as redistributed in https://github.com/OpenCLIM/ecocrop
  (file EcoCrop_DB.csv). Download it to data/external/EcoCrop_DB.csv, e.g.:
    git clone --depth 1 https://github.com/OpenCLIM/ecocrop.git data/external/ecocrop

Usage:
  python scripts/build_soil_suitability.py
  python scripts/build_soil_suitability.py --ecocrop path/to/EcoCrop_DB.csv
Output:
  backend/app/soil_suitability.json   (committed to git, read by the API)
"""

import argparse
import json
from pathlib import Path

import pandas as pd

# Our soil classes -> FAO texture classes.
#  - black soil (regur / vertisol) is made of very fine, clayey material -> heavy
#  - clay soil                                                           -> heavy
#  - alluvial soil is a mix of sand, silt and clay (loamy)               -> medium
#  - red soil is generally sandy to loamy and porous                     -> light
SOIL_TEXTURE = {
    "alluvial": "medium",
    "black": "heavy",
    "clay": "heavy",
    "red": "light",
}

# Kaggle crop label -> scientific name used in ECOCROP.
CROP_SPECIES = {
    "rice": "Oryza sativa",
    "maize": "Zea mays ssp. mays",   # plain "Zea mays" row has no soil data
    "chickpea": "Cicer arietinum",
    "kidneybeans": "Phaseolus vulgaris",
    "pigeonpeas": "Cajanus cajan",
    "mothbeans": "Vigna aconitifolia",
    "mungbean": "Vigna radiata",
    "blackgram": "Vigna mungo",
    "lentil": "Lens culinaris",
    "pomegranate": "Punica granatum",
    "banana": "Musa acuminata",
    "mango": "Mangifera indica",
    "grapes": "Vitis vinifera",
    "watermelon": "Citrullus lanatus",
    "muskmelon": "Cucumis melo",
    "apple": "Malus domestica",
    "orange": "Citrus sinensis",
    "papaya": "Carica papaya",
    "coconut": "Cocos nucifera",
    "cotton": "Gossypium hirsutum",
    "jute": "Corchorus capsularis",
    "coffee": "Coffea arabica",
}

ALL_TEXTURES = {"heavy", "medium", "light"}


def parse_textures(value) -> set:
    """'heavy, medium, organic' -> {'heavy', 'medium'}; 'wide' -> all textures."""
    if not isinstance(value, str):
        return set()
    parts = {p.strip().lower() for p in value.split(",")}
    if "wide" in parts:
        return set(ALL_TEXTURES)
    return parts & ALL_TEXTURES


def main():
    parser = argparse.ArgumentParser(description="Build soil suitability table from FAO ECOCROP.")
    parser.add_argument("--ecocrop", default="data/external/ecocrop/EcoCrop_DB.csv")
    parser.add_argument("--out", default="backend/app/soil_suitability.json")
    args = parser.parse_args()

    db = pd.read_csv(args.ecocrop, encoding="latin1")
    table, details = {soil: {} for soil in SOIL_TEXTURE}, {}

    for crop, species in CROP_SPECIES.items():
        rows = db[db["ScientificName"] == species]
        if rows.empty:
            raise SystemExit(f"'{species}' ({crop}) not found in ECOCROP")
        row = rows.iloc[0]
        optimal = parse_textures(row["TEXT"])
        absolute = parse_textures(row["TEXTR"]) | optimal
        if not optimal:
            raise SystemExit(f"No texture data for '{species}' ({crop})")
        details[crop] = {"species": species, "optimal": sorted(optimal), "absolute": sorted(absolute)}

        for soil, texture in SOIL_TEXTURE.items():
            if texture in optimal:
                rating = "good"
            elif texture in absolute:
                rating = "possible"
            else:
                rating = "poor"
            table[soil][crop] = rating

    out = {
        "source": "FAO ECOCROP database (soil texture: TEXT = optimal, TEXTR = absolute), "
                  "via https://github.com/OpenCLIM/ecocrop",
        "method": "soil class -> texture class; 'good' if texture is optimal for the crop, "
                  "'possible' if only tolerated, else 'poor'. Texture only - drainage, "
                  "salinity and local varieties are NOT considered.",
        "soil_texture": SOIL_TEXTURE,
        "ratings": table,
        "crop_textures": details,
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w") as f:
        json.dump(out, f, indent=2)

    # Print a readable table
    print(f"{'crop':<12}" + "".join(f"{s:>10}" for s in SOIL_TEXTURE))
    for crop in CROP_SPECIES:
        print(f"{crop:<12}" + "".join(f"{table[s][crop]:>10}" for s in SOIL_TEXTURE))
    print(f"\nSaved to {args.out}")


if __name__ == "__main__":
    main()
