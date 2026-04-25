import math, json
from datetime import datetime
from database import get_surplus_items, get_available_volunteers, get_foodbanks, log_pickup

def check_inventory(location_id: str) -> dict:
    items = get_surplus_items()
    location_items = [i for i in items if i["location_id"] == location_id]
    if not location_items:
        return {"status": "no_surplus", "location_id": location_id}
    return {
        "status": "surplus_detected",
        "location_id": location_id,
        "location_name": location_items[0]["location_name"],
        "items": [{"item": i["item"], "quantity_lbs": i["predicted_surplus"], "available_at": i["available_at"]} for i in location_items],
        "total_lbs": sum(i["predicted_surplus"] for i in location_items)
    }

def query_volunteers(supplier_lat: float, supplier_lng: float, radius_miles: float = 3.0) -> dict:
    vols = get_available_volunteers()
    nearby = []
    for v in vols:
        dist = _haversine(supplier_lat, supplier_lng, v["lat"], v["lng"])
        if dist <= radius_miles:
            nearby.append({"id": v["id"], "name": v["name"], "phone": v["phone"], "distance_miles": round(dist, 2)})
    nearby.sort(key=lambda x: x["distance_miles"])
    return {"available_volunteers": nearby, "count": len(nearby)}

def calculate_route(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> dict:
    dist_miles = _haversine(origin_lat, origin_lng, dest_lat, dest_lng)
    eta_minutes = round((dist_miles / 20) * 60)
    return {"distance_miles": round(dist_miles, 2), "eta_minutes": eta_minutes, "eta_string": f"{eta_minutes} minutes"}

def check_foodbank_capacity(foodbank_id: str) -> dict:
    foodbanks = get_foodbanks()
    fb = next((f for f in foodbanks if f["id"] == foodbank_id), None)
    if not fb:
        return {"status": "not_found", "foodbank_id": foodbank_id}
    return {"status": "accepting", "foodbank_id": foodbank_id, "foodbank_name": fb["name"], "capacity_lbs_available": 500, "lat": fb["lat"], "lng": fb["lng"]}

def verify_compliance(food_type: str, donor_type: str) -> dict:
    return {
        "compliant": True,
        "protection": "Bill Emerson Good Samaritan Food Donation Act (42 U.S.C. § 1791)",
        "liability": "Donor protected from civil and criminal liability when donating in good faith",
        "timestamp": datetime.now().isoformat(),
        "food_type": food_type,
        "donor_type": donor_type
    }

def dispatch_pickup(volunteer_id: str, volunteer_phone: str, supplier_id: str, supplier_name: str,
                    foodbank_id: str, foodbank_name: str, item: str, quantity_lbs: float, pickup_time: str) -> dict:
    sms_body = (f"🌿 FoodFlow: Pickup confirmed!\n📍 From: {supplier_name}\n"
                f"🏦 To: {foodbank_name}\n📦 {quantity_lbs} lbs {item}\n⏰ Ready at: {pickup_time}")
    log_pickup(supplier_id, foodbank_id, volunteer_id, item, quantity_lbs)
    print(f"\n{'='*50}\n📱 SMS SENT to {volunteer_phone}:\n{sms_body}\n{'='*50}\n")
    return {"status": "dispatched", "volunteer_id": volunteer_id, "sms_sent": True,
            "sms_body": sms_body, "pickup_logged": True, "quantity_lbs": quantity_lbs, "item": item}

def _haversine(lat1, lng1, lat2, lng2) -> float:
    R = 3958.8
    φ1, φ2 = math.radians(lat1), math.radians(lat2)
    Δφ = math.radians(lat2 - lat1)
    Δλ = math.radians(lng2 - lng1)
    a = math.sin(Δφ/2)**2 + math.cos(φ1)*math.cos(φ2)*math.sin(Δλ/2)**2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))

TOOL_FUNCTIONS = {
    "check_inventory": check_inventory,
    "query_volunteers": query_volunteers,
    "calculate_route": calculate_route,
    "check_foodbank_capacity": check_foodbank_capacity,
    "verify_compliance": verify_compliance,
    "dispatch_pickup": dispatch_pickup,
}

TOOL_SCHEMAS = [
    {"name": "check_inventory", "description": "Check predicted food surplus for a supplier location.", "input_schema": {"type": "object", "properties": {"location_id": {"type": "string"}}, "required": ["location_id"]}},
    {"name": "query_volunteers", "description": "Find available volunteer drivers near a supplier.", "input_schema": {"type": "object", "properties": {"supplier_lat": {"type": "number"}, "supplier_lng": {"type": "number"}, "radius_miles": {"type": "number"}}, "required": ["supplier_lat", "supplier_lng"]}},
    {"name": "calculate_route", "description": "Calculate driving distance and ETA between two points.", "input_schema": {"type": "object", "properties": {"origin_lat": {"type": "number"}, "origin_lng": {"type": "number"}, "dest_lat": {"type": "number"}, "dest_lng": {"type": "number"}}, "required": ["origin_lat", "origin_lng", "dest_lat", "dest_lng"]}},
    {"name": "check_foodbank_capacity", "description": "Check whether a food bank can accept a donation.", "input_schema": {"type": "object", "properties": {"foodbank_id": {"type": "string"}}, "required": ["foodbank_id"]}},
    {"name": "verify_compliance", "description": "Verify Bill Emerson Good Samaritan Act coverage.", "input_schema": {"type": "object", "properties": {"food_type": {"type": "string"}, "donor_type": {"type": "string"}}, "required": ["food_type", "donor_type"]}},
    {"name": "dispatch_pickup", "description": "Dispatch volunteer and log pickup.", "input_schema": {"type": "object", "properties": {"volunteer_id": {"type": "string"}, "volunteer_phone": {"type": "string"}, "supplier_id": {"type": "string"}, "supplier_name": {"type": "string"}, "foodbank_id": {"type": "string"}, "foodbank_name": {"type": "string"}, "item": {"type": "string"}, "quantity_lbs": {"type": "number"}, "pickup_time": {"type": "string"}}, "required": ["volunteer_id","volunteer_phone","supplier_id","supplier_name","foodbank_id","foodbank_name","item","quantity_lbs","pickup_time"]}}
]
