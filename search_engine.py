import requests
import time
import json

TV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tourvisor.ru/search.php"
}

hotel_cache = {}
region_cache = {}
operator_cache = {}

def get_operators():
    global operator_cache
    if operator_cache:
        return operator_cache
    try:
        r = requests.get("https://tourvisor.ru/xml/listdev.php?type=operator&format=json", headers=TV_HEADERS, timeout=8)
        data = r.json()
        op_list = data.get("lists", {}).get("operators", {}).get("operator", [])
        for o in op_list:
            operator_cache[o.get("id")] = o.get("name") or o.get("russian") or f"Оператор {o.get('id')}"
    except Exception as e:
        print(f"[Warn] get_operators error: {e}")
    return operator_cache

def get_country_catalogs(country_id):
    global hotel_cache, region_cache
    country_id = int(country_id)
    
    if country_id not in hotel_cache:
        try:
            print(f"[Catalog] Загрузка отелей страны {country_id}...")
            r = requests.get(f"https://tourvisor.ru/xml/listdev.php?type=allhotel&hotcountry={country_id}&format=json", headers=TV_HEADERS, timeout=12)
            data = r.json()
            h_list = data.get("lists", {}).get("hotels", {}).get("hotel", [])
            hotel_cache[country_id] = {h["id"]: h for h in h_list}
            print(f"[Catalog] Загружено {len(hotel_cache[country_id])} отелей для страны {country_id}.")
        except Exception as e:
            print(f"[Error] hotel catalog error: {e}")
            hotel_cache[country_id] = {}

    if country_id not in region_cache:
        try:
            print(f"[Catalog] Загрузка курортов страны {country_id}...")
            r = requests.get(f"https://tourvisor.ru/xml/listdev.php?type=region&hotcountry={country_id}&format=json", headers=TV_HEADERS, timeout=12)
            data = r.json()
            r_list = data.get("lists", {}).get("regions", {}).get("region", [])
            region_cache[country_id] = {reg["id"]: reg.get("name", "") for reg in r_list if reg.get("country") == country_id}
            print(f"[Catalog] Загружено {len(region_cache[country_id])} курортов для страны {country_id}.")
        except Exception as e:
            print(f"[Error] region catalog error: {e}")
            region_cache[country_id] = {}

    return hotel_cache[country_id], region_cache[country_id]

MEAL_MAP = {
    1: "Без питания (RO)",
    2: "Завтраки (BB)",
    3: "Завтрак + ужин (HB)",
    4: "Полный пансион (FB)",
    5: "Всё включено (AI)",
    6: "Ультра всё включено (UAI)"
}

def perform_full_search(country_id, datefrom, dateto, nightsfrom=6, nightsto=14, adults=2, child=0):
    hotels_cat, regions_cat = get_country_catalogs(country_id)
    ops_cat = get_operators()
    
    params = {
        "departure": 106, # Ташкент
        "country": country_id,
        "datefrom": datefrom,
        "dateto": dateto,
        "nightsfrom": nightsfrom,
        "nightsto": nightsto,
        "adults": adults,
        "child": child,
        "currency": 7, # USD / UZS
        "regular": 1,
        "directflight": 0,
        "format": "json"
    }
    
    print(f"[Search] Запуск modsearch: {params}")
    r = requests.get("https://tourvisor.ru/xml/modsearch.php", params=params, headers=TV_HEADERS, timeout=10)
    data = r.json()
    req_id = data.get("result", {}).get("requestid") or data.get("requestid")
    if not req_id:
        return {"error": "Не удалось получить ID поискового запроса", "raw": data}
        
    print(f"[Search] Request ID: {req_id}. Ожидание результатов от операторов...")
    
    # Wait for results: initial poll at 2.5s, second poll at 4.5s
    time.sleep(2.5)
    result_url = f"https://search3.tourvisor.ru/modresult.php?requestid={req_id}&format=json"
    r2 = requests.get(result_url, headers=TV_HEADERS, timeout=10)
    r2_data = r2.json()
    
    # Check if we should wait a bit more for more operators
    status = r2_data.get("data", {}).get("status", {})
    progress = status.get("progress", 0)
    try:
        prog_val = int(str(progress).replace('%', ''))
    except:
        prog_val = 0
    if prog_val < 90:
        time.sleep(2.0)
        try:
            r2 = requests.get(result_url, headers=TV_HEADERS, timeout=10)
            r2_data = r2.json()
        except:
            pass

    blocks = r2_data.get("data", {}).get("block", [])
    if not isinstance(blocks, list):
        blocks = [blocks] if blocks else []
        
    hotels_result = {}
    found_resorts = set()
    
    for blk in blocks:
        op_id = blk.get("operator")
        op_name = ops_cat.get(op_id, f"Оператор {op_id}")
        
        blk_hotels = blk.get("hotel", [])
        if not isinstance(blk_hotels, list):
            blk_hotels = [blk_hotels] if blk_hotels else []
            
        for h in blk_hotels:
            hid = h.get("id")
            if not hid:
                continue
                
            tours = h.get("tour", [])
            if not isinstance(tours, list):
                tours = [tours] if tours else []
                
            min_tour = None
            min_price_usd = float("inf")
            for t in tours:
                p_usd = t.get("prue")
                if p_usd and p_usd > 0 and p_usd < min_price_usd:
                    min_price_usd = p_usd
                    min_tour = t
                    
            if not min_tour:
                continue
                
            # If hotel already recorded, keep the cheaper option
            if hid in hotels_result:
                if min_price_usd < hotels_result[hid]["price_usd"]:
                    hotels_result[hid]["price_usd"] = min_price_usd
                    hotels_result[hid]["price_uzs"] = min_tour.get("prclean") or min_tour.get("pr") or 0
                    hotels_result[hid]["date"] = min_tour.get("dt", "")
                    hotels_result[hid]["nights"] = min_tour.get("nt", 7)
                    hotels_result[hid]["meal"] = MEAL_MAP.get(min_tour.get("ml"), f"Питание {min_tour.get('ml')}")
                    hotels_result[hid]["operator"] = op_name
                continue
                
            h_meta = hotels_cat.get(hid, {})
            h_name = h_meta.get("name", f"Отель #{hid}")
            stars = int(h_meta.get("stars") or 0)
            rating = round(float(h_meta.get("rating") or 4.0), 1)
            reg_code = h_meta.get("regioncode") or h_meta.get("region") or 0
            reg_name = regions_cat.get(reg_code, "Курорт")
            found_resorts.add(reg_name)
            
            hotels_result[hid] = {
                "hotel_id": hid,
                "name": h_name,
                "stars": stars,
                "rating": rating if rating > 0 else 4.2,
                "region": reg_name,
                "price_usd": min_price_usd,
                "price_uzs": min_tour.get("prclean") or min_tour.get("pr") or 0,
                "date": min_tour.get("dt", ""),
                "nights": min_tour.get("nt", 7),
                "meal": MEAL_MAP.get(min_tour.get("ml"), f"Питание {min_tour.get('ml')}") if min_tour.get("ml") else "Стандартное",
                "operator": op_name,
                "photo": f"https://static.tourvisor.ru/hotel_pics/medium/{hid}.jpg"
            }
            
    sorted_hotels = sorted(hotels_result.values(), key=lambda x: x["price_usd"])
    
    return {
        "success": True,
        "count": len(sorted_hotels),
        "request_id": req_id,
        "hotels": sorted_hotels,
        "resorts": sorted(list(found_resorts))
    }

if __name__ == "__main__":
    t0 = time.time()
    res = perform_full_search(2, "27.09.2026", "06.10.2026", 6, 14, 2)
    print(f"Поиск завершен за {round(time.time() - t0, 2)} сек! Найдено отелей: {res.get('count')}")
    print("Курорты:", res.get("resorts"))
    for h in res.get("hotels", [])[:5]:
        print(f"-> {h['name']} ({h['stars']}*) - {h['region']} | ${h['price_usd']} / {h['price_uzs']} UZS | {h['nights']} ночей, вылет {h['date']} | {h['operator']}")
