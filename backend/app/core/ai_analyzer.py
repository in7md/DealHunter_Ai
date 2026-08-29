import httpx
from app.config import settings
from app.database.models import ScoredDeal

class AIAnalyzer:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY

    async def analyze_deal(self, deal: ScoredDeal) -> str:
        if not self.api_key:
            return "AI Analysis unavailable: Missing API key."
            
        prompt = f"""
        You are an expert car appraiser and market analyst. Analyze this deal quickly and provide a 2-3 sentence insight on negotiation tactics, potential red flags, and the real value.
        
        Car: {deal.listing.year} {deal.listing.make} {deal.listing.model}
        Price: {deal.listing.price_bhd} BHD
        Mileage: {deal.listing.mileage_km} km (Expected: {deal.expected_mileage} km)
        Desc: {deal.listing.description}
        Calculated Adjusted Market Value: {deal.adjusted_market_value} BHD
        Net Profit: {deal.net_profit} BHD
        """
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(url, json=payload, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates", [])
                    if candidates:
                        return candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "No insight generated.")
                return f"AI Analysis Error: {response.status_code} - {response.text}"
        except Exception as e:
            return f"AI Analysis Error: {str(e)}"

    async def extract_car_details(self, caption: str) -> dict | None:
        if not self.api_key:
            return None
            
        prompt = f"""
        Extract the following details from this car listing caption. Return ONLY a valid JSON object with the exact keys:
        - "make" (string, e.g. Toyota, or null if missing)
        - "model" (string, e.g. Camry, or null if missing)
        - "year" (integer, 4 digits, or null if missing)
        - "price" (integer, extract the price in BHD. Strip currencies. Set to null if missing, unclear, or says "call for price")
        - "mileage" (integer, extract the mileage in km. Convert from miles if necessary. Set to null if missing)
        
        Caption:
        {caption}
        """
        
        headers = {"Content-Type": "application/json"}
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.1,
                "response_mime_type": "application/json"
            }
        }
        
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={self.api_key}"
        
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                if response.status_code == 200:
                    data = response.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    # Extract JSON block just in case
                    start = text.find("{")
                    end = text.rfind("}") + 1
                    if start != -1 and end != 0:
                        json_str = text[start:end]
                        return json.loads(json_str)
                return None
        except Exception as e:
            print(f"Gemini Extraction Error: {e}")
            return None
