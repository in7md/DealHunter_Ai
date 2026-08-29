import re
from typing import Tuple, Optional

# Comprehensive dictionary of car makes and their popular models in the GCC market
CAR_KNOWLEDGE_BASE = {
    "toyota": ["camry", "corolla", "land cruiser", "prado", "yaris", "hilux", "rav4", "avalon", "fortuner", "fj cruiser", "innova", "aurion", "supra", "chr", "crown"],
    "nissan": ["patrol", "altima", "sunny", "maxima", "pathfinder", "kicks", "x-trail", "xtrail", "sentra", "navara", "z", "armada", "tiida", "micra"],
    "honda": ["accord", "civic", "cr-v", "crv", "pilot", "hr-v", "hrv", "city", "odyssey"],
    "lexus": ["lx", "ls", "es", "rx", "is", "nx", "gx", "rc", "lc"],
    "hyundai": ["sonata", "elantra", "tucson", "santa fe", "accent", "creta", "azera", "palisade", "kona"],
    "kia": ["optima", "sportage", "sorento", "cerato", "rio", "telluride", "k5", "seltos", "cadenza", "picanto", "carnival"],
    "ford": ["mustang", "explorer", "f-150", "f150", "expedition", "edge", "escape", "ranger", "taurus", "bronco"],
    "chevrolet": ["tahoe", "silverado", "camaro", "corvette", "malibu", "captiva", "traverse", "impala", "suburban", "equinox"],
    "mazda": ["3", "6", "cx-5", "cx5", "cx-9", "cx9", "cx-30", "cx30"],
    "mercedes": ["c-class", "e-class", "s-class", "a-class", "g-class", "gle", "glc", "gls", "cla", "g63", "amg"],
    "mercedes-benz": ["c-class", "e-class", "s-class", "a-class", "g-class", "gle", "glc", "gls", "cla", "g63", "amg"],
    "bmw": ["3 series", "5 series", "7 series", "x5", "x6", "x3", "x7", "m3", "m4", "m5"],
    "mg": ["rx5", "zs", "hs", "mg5", "mg6", "rx8", "gt"],
    "geely": ["coolray", "azkarra", "tugella", "monjaro", "emgrand"],
    "changan": ["cs75", "cs85", "cs95", "cs35", "uni-t", "uni-k", "uni-v", "eado"],
    "jetour": ["dashing", "x70", "x90"],
    "audi": ["a3", "a4", "a6", "a8", "q3", "q5", "q7", "q8", "rs"],
    "volkswagen": ["golf", "passat", "tiguan", "touareg", "teramont", "jetta"],
    "land rover": ["range rover", "defender", "discovery", "velar", "evoque"],
    "porsche": ["911", "cayenne", "macan", "panamera", "taycan", "boxster", "cayman"],
    "mitsubishi": ["pajero", "lancer", "outlander", "montero", "asx", "attrage", "eclipse"],
    "subaru": ["wrx", "sti", "brz", "forester", "outback", "crosstrek", "impreza"],
    "suzuki": ["jimny", "swift", "vitara", "ertiga", "baleno", "dzire"],
    "isuzu": ["d-max", "mux"],
    "gmc": ["yukon", "sierra", "acadia", "terrain"],
    "dodge": ["charger", "challenger", "durango", "ram"],
    "jeep": ["wrangler", "grand cherokee", "compass", "gladiator"],
    "chrysler": ["300", "pacifica"],
    "infiniti": ["q50", "qx50", "qx60", "qx80", "q60"],
    "acura": ["mdx", "rdx", "tlx"],
    "cadillac": ["escalade", "ct4", "ct5", "xt4", "xt5", "xt6"],
    "lincoln": ["navigator", "aviator", "corsair", "nautilus"],
    "volvo": ["xc90", "xc60", "xc40", "s90", "s60", "v90"],
    "peugeot": ["208", "308", "508", "2008", "3008", "5008"],
    "renault": ["duster", "megane", "symbol", "koleos", "clio"],
    "chery": ["tiggo 8", "tiggo 7", "tiggo 4", "arrizo", "tiggo"],
    "haval": ["h6", "jolion", "h9", "darqo"],
    "genesis": ["g70", "g80", "g90", "gv70", "gv80"],
    "mini": ["cooper", "countryman", "clubman"],
    "jaguar": ["f-pace", "e-pace", "xj", "xf", "xe", "f-type"],
}

def extract_make_model_fallback(raw_title: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Deterministically extracts the Make and Model of a car from a messy title string.
    Returns (Make, Model) or (None, None) if not found.
    """
    if not raw_title:
        return None, None
        
    title_lower = raw_title.lower()
    
    # 1. Identify Make
    found_make = None
    make_key = None
    for make in CAR_KNOWLEDGE_BASE.keys():
        # Match as whole word
        if re.search(rf'\b{re.escape(make)}\b', title_lower):
            found_make = make.title() if make != "bmw" and make != "mg" else make.upper()
            make_key = make
            break
            
    if not found_make:
        return None, None

    # 2. Identify Model
    found_model = None
    models = CAR_KNOWLEDGE_BASE[make_key]
    
    # Sort models by length descending to match longest first (e.g., "Land Cruiser" before "Land")
    models.sort(key=len, reverse=True)
    
    for model in models:
        if re.search(rf'\b{re.escape(model)}\b', title_lower):
            found_model = model.title() if model not in ["x5", "x6", "cx-5", "f-150"] else model.upper()
            break
            
    # 3. Fallback Model extraction if dictionary missed it
    if not found_model:
        # Extract the word immediately following the Make
        match = re.search(rf'\b{re.escape(make_key)}\b\s+([a-z0-9\-]+)', title_lower)
        if match:
            candidate = match.group(1)
            # Filter out years or stop words
            if not re.match(r'^(19|20)\d{2}$', candidate) and candidate not in ["for", "sale", "model", "series"]:
                found_model = candidate.title()

    if not found_model:
        found_model = "Standard" # Safe fallback for model if make is known

    return found_make, found_model
