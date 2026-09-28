import http.server
import urllib.parse
import json
import requests
import os
import time
from datetime import datetime

PORT = 8050

TV_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://tourvisor.ru/search.php"
}

# Кэш в оперативной памяти
hotel_cache = {}
region_cache = {}
operator_cache = {}
countries_cache = {}

# Точные коды питания Tourvisor API
MEAL_MAP = {
    1: "Без питания (RO)",
    2: "Без питания (RO)",
    3: "Завтраки (BB)",
    4: "Завтрак + ужин (HB)",
    5: "Полный пансион (FB)",
    7: "Всё включено (AI)",
    9: "Ультра всё включено (UAI)"
}

TELEGRAM_BOT_TOKEN = "8872361930:AAEdil-ITnEFsR2NopF9Vc_SMCa6xLHd2qA"
cached_chat_ids = set()

UMRAH_COUNTRY = {
    "id": 999,
    "name": "🕋 Умра 2026 (Мекка & Медина)",
    "group": "umrah",
    "flag": "🕋"
}

UMRAH_PACKAGES = [
    {
        "hotel_id": 99901,
        "name": "🕋 VIP Пакет: Pullman ZamZam 5★ (1-я линия Харам)",
        "stars": 5,
        "rating": 4.9,
        "region": "Мекка (10н) + Медина (4н)",
        "price_usd": 1650,
        "price_uzs": 22600000,
        "date": "05.10.2026",
        "dates_available": ["05.10.2026", "12.10.2026", "19.10.2026", "26.10.2026"],
        "nights": 14,
        "meal": "HB (Завтрак + Ужин шведский стол)",
        "operator": "Turon Travel (Эксклюзив)",
        "photo": "https://images.unsplash.com/photo-1591604129939-f1efa4d9f7fa?auto=format&fit=crop&w=800&q=80",
        "photo_large": "https://images.unsplash.com/photo-1591604129939-f1efa4d9f7fa?auto=format&fit=crop&w=1200&q=80",
        "is_exclusive": True,
        "badge": "👑 VIP Первая линия Харам",
        "description": "50 метров до Каабы в комплексе Abraj Al Bait. Прямой перелет, виза Умра, VIP-трансферы, гид-элликбоши, экскурсии, подарок 5L Замзам + фирменный набор паломника."
    },
    {
        "hotel_id": 99902,
        "name": "🕋 Комфорт Плюс: Swissôtel Al Maqam 5★",
        "stars": 5,
        "rating": 4.8,
        "region": "Мекка (10н) + Медина (4н)",
        "price_usd": 1390,
        "price_uzs": 19000000,
        "date": "05.10.2026",
        "dates_available": ["05.10.2026", "12.10.2026", "19.10.2026"],
        "nights": 14,
        "meal": "BB (Завтраки шведский стол)",
        "operator": "Turon Travel (Эксклюзив)",
        "photo": "https://images.unsplash.com/photo-1564769625905-50e93615e769?auto=format&fit=crop&w=800&q=80",
        "photo_large": "https://images.unsplash.com/photo-1564769625905-50e93615e769?auto=format&fit=crop&w=1200&q=80",
        "is_exclusive": True,
        "badge": "⭐ Комплекс Abraj Al Bait",
        "description": "Прямой доступ в мечеть Аль-Харам. Виза Умра, комфортабельные автобусы Mercedes, гид, посещение горы Ухуд, Куба, вода Замзам."
    },
    {
        "hotel_id": 99903,
        "name": "🕋 Стандарт: Voco Makkah 4★ (IHG)",
        "stars": 4,
        "rating": 4.6,
        "region": "Мекка (7н) + Медина (3н)",
        "price_usd": 1150,
        "price_uzs": 15750000,
        "date": "12.10.2026",
        "dates_available": ["12.10.2026", "19.10.2026", "26.10.2026"],
        "nights": 10,
        "meal": "BB (Завтраки)",
        "operator": "Turon Travel (Эксклюзив)",
        "photo": "https://images.unsplash.com/photo-1542816417-0983c9c9ad53?auto=format&fit=crop&w=800&q=80",
        "photo_large": "https://images.unsplash.com/photo-1542816417-0983c9c9ad53?auto=format&fit=crop&w=1200&q=80",
        "is_exclusive": True,
        "badge": "🚌 Бесплатный шатл 24/7",
        "description": "Круглосуточный шатл каждые 3 минуты до мечети. Виза Умра, прямой рейс, медицинская страховка, сопровождение, вода Замзам."
    },
    {
        "hotel_id": 99904,
        "name": "🕋 Эконом Пакет: Al Kiswah Towers 3★",
        "stars": 3,
        "rating": 4.4,
        "region": "Мекка (10н) + Медина (4н)",
        "price_usd": 950,
        "price_uzs": 13000000,
        "date": "05.10.2026",
        "dates_available": ["05.10.2026", "12.10.2026", "19.10.2026"],
        "nights": 14,
        "meal": "Без питания (RO)",
        "operator": "Turon Travel (Эксклюзив)",
        "photo": "https://images.unsplash.com/photo-1565552645632-d725f8bfc19a?auto=format&fit=crop&w=800&q=80",
        "photo_large": "https://images.unsplash.com/photo-1565552645632-d725f8bfc19a?auto=format&fit=crop&w=1200&q=80",
        "is_exclusive": True,
        "badge": "🔥 Выгодная цена / Хиджаз",
        "description": "Доступный качественный пакет для паломников. Бесплатный автобус до Харама, виза Умра, прямой авиаперелет, опытный гид, вода Замзам."
    }
]

CHARTER_COUNTRIES = [
    {"id": 2, "name": "🇹🇭 Таиланд", "group": "charter", "flag": "🇹🇭"},
    {"id": 4, "name": "🇹🇷 Турция", "group": "charter", "flag": "🇹🇷"},
    {"id": 1, "name": "🇪🇬 Египет", "group": "charter", "flag": "🇪🇬"},
    {"id": 9, "name": "🇦🇪 ОАЭ", "group": "charter", "flag": "🇦🇪"},
    {"id": 16, "name": "🇻🇳 Вьетнам", "group": "charter", "flag": "🇻🇳"},
    {"id": 8, "name": "🇲🇻 Мальдивы", "group": "charter", "flag": "🇲🇻"},
    {"id": 12, "name": "🇱🇰 Шри-Ланка", "group": "charter", "flag": "🇱🇰"},
    {"id": 3, "name": "🇮🇳 Индия (Гоа)", "group": "charter", "flag": "🇮🇳"},
    {"id": 35, "name": "🇲🇾 Малайзия", "group": "charter", "flag": "🇲🇾"},
    {"id": 7, "name": "🇮🇩 Индонезия (Бали)", "group": "charter", "flag": "🇮🇩"},
    {"id": 13, "name": "🇨🇳 Китай (о. Хайнань)", "group": "charter", "flag": "🇨🇳"},
    {"id": 79, "name": "🇶🇦 Катар", "group": "charter", "flag": "🇶🇦"},
    {"id": 54, "name": "🇬🇪 Грузия", "group": "charter", "flag": "🇬🇪"},
    {"id": 55, "name": "🇦🇿 Азербайджан", "group": "charter", "flag": "🇦🇿"},
    {"id": 64, "name": "🇴🇲 Оман", "group": "charter", "flag": "🇴🇲"}
]

INDIVIDUAL_COUNTRIES = [
    {"id": 32, "name": "🇫🇷 Франция (Париж, Лазурный берег)", "group": "individual", "flag": "🇫🇷"},
    {"id": 24, "name": "🇮🇹 Италия (Рим, Милан, Венеция)", "group": "individual", "flag": "🇮🇹"},
    {"id": 14, "name": "🇪🇸 Испания (Барселона, Каталония)", "group": "individual", "flag": "🇪🇸"},
    {"id": 6, "name": "🇬🇷 Греция", "group": "individual", "flag": "🇬🇷"},
    {"id": 31, "name": "🇦🇹 Австрия", "group": "individual", "flag": "🇦🇹"},
    {"id": 37, "name": "🇭🇺 Венгрия", "group": "individual", "flag": "🇭🇺"},
    {"id": 15, "name": "🇨🇾 Кипр", "group": "individual", "flag": "🇨🇾"},
    {"id": 21, "name": "🇲🇪 Черногория", "group": "individual", "flag": "🇲🇪"},
    {"id": 19, "name": "🇨🇿 Чехия", "group": "individual", "flag": "🇨🇿"}
]

INDIVIDUAL_COUNTRY_IDS = {c["id"] for c in INDIVIDUAL_COUNTRIES}

DEPARTURES = [
    {"id": 106, "name": "Ташкент (TAS)", "code": "TAS"},
    {"id": 125, "name": "Самарканд (SKD)", "code": "SKD"}
]

# Наценка турагентства (0% по умолчанию, можно задать например 2.0 для +2%)
AGENCY_MARKUP_PERCENT = 0.0

def get_countries(departure_id=106):
    global countries_cache
    dep_id = int(departure_id)
    if dep_id in countries_cache:
        return countries_cache[dep_id]
        
    combined = {
        "umrah": [UMRAH_COUNTRY],
        "charter": CHARTER_COUNTRIES,
        "individual": INDIVIDUAL_COUNTRIES,
        "countries": [UMRAH_COUNTRY] + CHARTER_COUNTRIES + INDIVIDUAL_COUNTRIES
    }
    countries_cache[dep_id] = combined
    return combined

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
            print(f"[Catalog] Загрузка базы отелей для страны ID={country_id}...")
            r = requests.get(f"https://tourvisor.ru/xml/listdev.php?type=allhotel&hotcountry={country_id}&format=json", headers=TV_HEADERS, timeout=12)
            data = r.json()
            h_list = data.get("lists", {}).get("hotels", {}).get("hotel", [])
            hotel_cache[country_id] = {h["id"]: h for h in h_list}
            print(f"[Catalog] Готово: {len(hotel_cache[country_id])} отелей.")
        except Exception as e:
            print(f"[Error] hotel catalog: {e}")
            hotel_cache[country_id] = {}

    if country_id not in region_cache:
        try:
            print(f"[Catalog] Загрузка курортов для страны ID={country_id}...")
            r = requests.get(f"https://tourvisor.ru/xml/listdev.php?type=region&hotcountry={country_id}&format=json", headers=TV_HEADERS, timeout=12)
            data = r.json()
            r_list = data.get("lists", {}).get("regions", {}).get("region", [])
            region_cache[country_id] = {reg["id"]: reg.get("name", "") for reg in r_list if reg.get("country") == country_id}
            print(f"[Catalog] Готово: {len(region_cache[country_id])} курортов.")
        except Exception as e:
            print(f"[Error] region catalog: {e}")
            region_cache[country_id] = {}

    return hotel_cache[country_id], region_cache[country_id]

def execute_full_search(country_id, datefrom, dateto, nightsfrom=6, nightsto=14, adults=2, child=0, child_ages=None, stars=0, meal=0, regions=None, hotels=None, departure=106):
    if int(country_id) == 999:
        filtered = list(UMRAH_PACKAGES)
        if stars and int(stars) > 0:
            filtered = [u for u in filtered if u["stars"] >= int(stars)]
        if meal and int(meal) > 0:
            if int(meal) == 4:
                filtered = [u for u in filtered if "HB" in u["meal"]]
            elif int(meal) == 3:
                filtered = [u for u in filtered if "BB" in u["meal"] or "HB" in u["meal"]]
        return {
            "success": True,
            "count": len(filtered),
            "is_individual": False,
            "is_umrah": True,
            "country_id": 999,
            "request_id": 999999,
            "hotels": filtered,
            "resorts": ["Мекка (Харам)", "Медина (Масджид ан-Набави)"],
            "operators": ["Turon Travel (Эксклюзив)"]
        }

    hotels_cat, regions_cat = get_country_catalogs(country_id)
    ops_cat = get_operators()
    
    params = {
        "departure": departure,
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

    # Возраста детей
    if child > 0 and child_ages:
        for idx, age in enumerate(child_ages[:3], 1):
            params[f"childage{idx}"] = age

    # Звездность
    if stars and int(stars) > 0:
        params["stars"] = stars

    # Питание (AI=7, UAI=9, BB=3, HB=4, FB=5)
    if meal and int(meal) > 0:
        params["meal"] = meal

    # Конкретные курорты
    if regions:
        params["regions"] = regions

    # Конкретный отель
    if hotels:
        params["hotels"] = hotels
    
    print(f"[FullSearch] Запрос: country={country_id}, {datefrom}-{dateto}, {nightsfrom}-{nightsto}н, {adults}взр+{child}дет, stars={stars}, meal={meal}, dep={departure}")
    try:
        r = requests.get("https://tourvisor.ru/xml/modsearch.php", params=params, headers=TV_HEADERS, timeout=10)
        data = r.json()
    except Exception as e:
        return {"error": f"Ошибка связи с поисковым сервером: {e}"}

    req_id = data.get("result", {}).get("requestid") or data.get("requestid")
    if not req_id:
        return {"error": "Не удалось получить ID поискового запроса", "raw": data}
        
    print(f"[FullSearch] Request ID: {req_id}. Сбор результатов от туроператоров...")
    
    # Опрос результатов
    time.sleep(2.5)
    result_url = f"https://search3.tourvisor.ru/modresult.php?requestid={req_id}&format=json"
    try:
        r2 = requests.get(result_url, headers=TV_HEADERS, timeout=10)
        r2_data = r2.json()
    except Exception as e:
        return {"error": f"Ошибка получения результатов: {e}"}

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
    found_operators = set()
    
    for blk in blocks:
        op_id = blk.get("operator")
        op_name = ops_cat.get(op_id, f"Оператор {op_id}")
        found_operators.add(op_name)
        
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
            
            # Применение наценки агентства, если задана
            final_usd = round(min_price_usd * (1 + AGENCY_MARKUP_PERCENT / 100))
            raw_uzs = min_tour.get("prclean") or min_tour.get("pr") or 0
            final_uzs = round(raw_uzs * (1 + AGENCY_MARKUP_PERCENT / 100))
                
            # Если отель уже записан, сохраняем лучшую цену
            if hid in hotels_result:
                if final_usd < hotels_result[hid]["price_usd"]:
                    hotels_result[hid]["price_usd"] = final_usd
                    hotels_result[hid]["price_uzs"] = final_uzs
                    hotels_result[hid]["date"] = min_tour.get("dt", "")
                    hotels_result[hid]["nights"] = min_tour.get("nt", 7)
                    hotels_result[hid]["meal"] = MEAL_MAP.get(min_tour.get("ml"), f"Питание {min_tour.get('ml')}")
                    hotels_result[hid]["operator"] = op_name
                continue
                
            h_meta = hotels_cat.get(hid, {})
            h_name = h_meta.get("name", f"Отель #{hid}")
            stars_val = int(h_meta.get("stars") or 0)
            rating = round(float(h_meta.get("rating") or 4.2), 1)
            reg_code = h_meta.get("regioncode") or h_meta.get("region") or 0
            reg_name = regions_cat.get(reg_code, "Курорт")
            found_resorts.add(reg_name)
            
            hotels_result[hid] = {
                "hotel_id": hid,
                "name": h_name,
                "stars": stars_val,
                "rating": rating if rating > 0 else 4.2,
                "region": reg_name,
                "price_usd": final_usd,
                "price_uzs": final_uzs,
                "date": min_tour.get("dt", ""),
                "nights": min_tour.get("nt", 7),
                "meal": MEAL_MAP.get(min_tour.get("ml"), f"Питание {min_tour.get('ml')}") if min_tour.get("ml") else "Стандартное",
                "operator": op_name,
                "photo": f"https://static.tourvisor.ru/hotel_pics/medium/{hid}.jpg",
                "photo_large": f"https://static.tourvisor.ru/hotel_pics/main400/{hid}.jpg"
            }
            
    sorted_hotels = sorted(hotels_result.values(), key=lambda x: x["price_usd"])
    
    is_individual = int(country_id) in INDIVIDUAL_COUNTRY_IDS
    return {
        "success": True,
        "count": len(sorted_hotels),
        "is_individual": is_individual,
        "country_id": int(country_id),
        "request_id": req_id,
        "hotels": sorted_hotels,
        "resorts": sorted(list(found_resorts)),
        "operators": sorted(list(found_operators))
    }

def autocomplete_hotels(country_id, query):
    hotels_cat, regions_cat = get_country_catalogs(country_id)
    q = query.strip().lower()
    if not q:
        return []
    
    results = []
    for hid, h in hotels_cat.items():
        name = h.get("name", "")
        if q in name.lower():
            reg_code = h.get("regioncode") or h.get("region") or 0
            results.append({
                "id": hid,
                "name": name,
                "stars": int(h.get("stars") or 0),
                "region": regions_cat.get(reg_code, "")
            })
            if len(results) >= 15:
                break
    return results

def get_telegram_chat_ids():
    global cached_chat_ids
    if os.path.exists("tg_chats.json"):
        try:
            with open("tg_chats.json", "r", encoding="utf-8") as f:
                saved = json.load(f)
                for cid in saved:
                    cached_chat_ids.add(cid)
        except Exception as e:
            print(f"[TG] Read tg_chats.json: {e}")

    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getUpdates"
        r = requests.get(url, timeout=4)
        if r.status_code == 200:
            data = r.json()
            for u in data.get("result", []):
                msg = u.get("message") or u.get("channel_post") or u.get("my_chat_member") or {}
                chat = msg.get("chat", {})
                cid = chat.get("id")
                if cid:
                    cached_chat_ids.add(cid)
            if cached_chat_ids:
                with open("tg_chats.json", "w", encoding="utf-8") as f:
                    json.dump(list(cached_chat_ids), f)
    except Exception as e:
        print(f"[TG] getUpdates: {e}")
    return list(cached_chat_ids)

def send_telegram_lead(lead_data):
    chat_ids = get_telegram_chat_ids()
    if not chat_ids:
        print("[TG] Заявка сохранена в leads.json! (Чтобы получать в Telegram, напишите /start боту @turonb2c_bot)")
        return False
        
    client_name = lead_data.get("client_name") or "Не указано"
    client_phone = lead_data.get("client_phone") or "Не указано"
    hotel_name = lead_data.get("hotel_name") or "Тур"
    stars = lead_data.get("stars") or 5
    try:
        stars_val = int(stars)
        stars_str = "⭐" * stars_val
    except:
        stars_str = ""
    date_str = lead_data.get("date") or "Уточняется"
    nights = lead_data.get("nights") or 7
    meal = lead_data.get("meal") or "Стандарт"
    price_usd = lead_data.get("price_usd") or 0
    price_uzs = lead_data.get("price_uzs") or 0
    operator = lead_data.get("operator") or "Эксклюзив"

    is_umrah = "умра" in hotel_name.lower() or "umrah" in hotel_name.lower() or "мекка" in hotel_name.lower()
    header = "🕋 <b>НОВАЯ ЗАЯВКА НА УМРУ!</b>" if is_umrah else "🔥 <b>НОВАЯ ЗАЯВКА НА ТУР!</b>"
    
    formatted_uzs = f"{price_uzs:,}".replace(",", " ")
    text = (
        f"{header}\n\n"
        f"👤 <b>Клиент:</b> {client_name}\n"
        f"📞 <b>Телефон:</b> <code>{client_phone}</code>\n"
        f"🏨 <b>Тур / Пакет:</b> {hotel_name} {stars_str}\n"
        f"📅 <b>Даты:</b> {date_str} ({nights} ночей)\n"
        f"🍽 <b>Питание:</b> {meal}\n"
        f"💰 <b>Цена:</b> <b>${price_usd}</b> ({formatted_uzs} сум)\n"
        f"🏢 <b>Программа:</b> {operator}\n\n"
        f"⏰ <i>{datetime.now().strftime('%d.%m.%Y %H:%M:%S')}</i>"
    )

    success = False
    for cid in chat_ids:
        try:
            r = requests.post(
                f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage",
                json={
                    "chat_id": cid,
                    "text": text,
                    "parse_mode": "HTML"
                },
                timeout=5
            )
            if r.status_code == 200:
                print(f"[TG] Уведомление доставлено в Telegram (chat_id: {cid})!")
                success = True
            else:
                print(f"[TG] Ошибка отправки в {cid}: {r.text}")
        except Exception as e:
            print(f"[TG] Ошибка отправки: {e}")
    return success

def save_lead(lead_data):
    leads_file = "leads.json"
    lead_data["created_at"] = datetime.now().isoformat()
    leads = []
    if os.path.exists(leads_file):
        try:
            with open(leads_file, "r", encoding="utf-8") as f:
                leads = json.load(f)
        except:
            leads = []
    leads.append(lead_data)
    with open(leads_file, "w", encoding="utf-8") as f:
        json.dump(leads, f, ensure_ascii=False, indent=2)
    print(f"[LEAD] Новая заявка на тур: {lead_data.get('client_name')}, тел: {lead_data.get('client_phone')}, отель: {lead_data.get('hotel_name')} (${lead_data.get('price_usd')})")
    
    # Отправка в Telegram
    try:
        send_telegram_lead(lead_data)
    except Exception as e:
        print(f"[TG] Error in background sender: {e}")

    return {"success": True, "message": "Заявка успешно зарегистрирована! Менеджер свяжется с вами."}

class LiveTourHandler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/submit_lead":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            try:
                lead_data = json.loads(post_body.decode("utf-8"))
                result = save_lead(lead_data)
            except Exception as e:
                result = {"success": False, "error": str(e)}
            self._send_json(result)
        else:
            self.send_error(404, "Endpoint not found")

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/api/departures":
            self._send_json({"departures": DEPARTURES})

        elif parsed.path == "/api/countries":
            dep = int(qs.get("departure", ["106"])[0])
            c_data = get_countries(dep)
            self._send_json(c_data)

        elif parsed.path == "/api/autocomplete_hotels":
            country_id = int(qs.get("country", ["2"])[0])
            q = qs.get("q", [""])[0]
            matches = autocomplete_hotels(country_id, q)
            self._send_json({"hotels": matches})

        elif parsed.path == "/api/full_search":
            country_id = int(qs.get("country", ["2"])[0])
            departure = int(qs.get("departure", ["106"])[0])
            datefrom = qs.get("datefrom", ["27.09.2026"])[0]
            dateto = qs.get("dateto", ["06.10.2026"])[0]
            nightsfrom = int(qs.get("nightsfrom", ["6"])[0])
            nightsto = int(qs.get("nightsto", ["14"])[0])
            adults = int(qs.get("adults", ["2"])[0])
            child = int(qs.get("child", ["0"])[0])
            
            # Чтение возрастов детей (например "4,9")
            child_ages_raw = qs.get("child_ages", [""])[0]
            child_ages = [int(a.strip()) for a in child_ages_raw.split(",") if a.strip().isdigit()]

            stars = int(qs.get("stars", ["0"])[0])
            meal = int(qs.get("meal", ["0"])[0])
            regions = qs.get("regions", [None])[0]
            hotels = qs.get("hotels", [None])[0]

            result = execute_full_search(
                country_id=country_id,
                datefrom=datefrom,
                dateto=dateto,
                nightsfrom=nightsfrom,
                nightsto=nightsto,
                adults=adults,
                child=child,
                child_ages=child_ages,
                stars=stars,
                meal=meal,
                regions=regions,
                hotels=hotels,
                departure=departure
            )
            self._send_json(result)

        else:
            super().do_GET()

    def _send_json(self, data):
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))

class ThreadedHTTPServer(http.server.ThreadingHTTPServer):
    allow_reuse_address = True

def run_server():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    server = ThreadedHTTPServer(("", PORT), LiveTourHandler)
    print(f"Сервер Турвизор-шлюза запущен: http://localhost:{PORT}")
    server.serve_forever()

if __name__ == "__main__":
    run_server()
