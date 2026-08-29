import hashlib
from app.database.models import RawListing

class Deduplicator:
    @staticmethod
    def generate_fingerprint(listing: RawListing) -> str:
        # fingerprint_hash = SHA256 of phone + make + model + year + rounded_price
        rounded_price = round(listing.price_bhd)
        phone = listing.phone or ""
        make = listing.make.lower()
        model = listing.model.lower()
        year = str(listing.year)
        
        raw_string = f"{listing.source}{listing.source_id}{phone}{make}{model}{year}{rounded_price}"
        return hashlib.sha256(raw_string.encode('utf-8')).hexdigest()
