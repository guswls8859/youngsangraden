"""기상예보 유틸리티

우선순위:
1. 기상청 단기예보 API (data.go.kr) — settings.KMA_API_KEY 설정 시 사용
2. Open-Meteo (무료, 키 불필요) — 폴백

캐시: 같은 날짜 결과는 메모리에 1시간 보관 (매 요청마다 API 호출 방지)
"""
import datetime
import json
import time
import urllib.request
import urllib.parse

# 메모리 캐시: {report_date: (result_dict, cached_at_timestamp)}
_cache: dict = {}
_CACHE_TTL = 3600  # 1시간

# 용산어린이정원 위경도
_LAT = 37.5307
_LON = 126.9701

# 기상청 격자 좌표 (용산구)
_KMA_NX = 60
_KMA_NY = 126

# 기상청 단기예보 발표 시각 (KST)
_BASE_HOURS = [2, 5, 8, 11, 14, 17, 20, 23]


def _kma_base_time(now: datetime.datetime):
    """현재 시각 기준으로 가장 최근 발표 base_date, base_time 반환"""
    # 발표 후 약 10분 뒤 데이터 제공 — 여유 있게 20분 이전 발표분 사용
    adjusted = now - datetime.timedelta(minutes=20)
    for h in reversed(_BASE_HOURS):
        if adjusted.hour >= h:
            return adjusted.strftime('%Y%m%d'), f'{h:02d}00'
    # 자정~02:20 사이: 전날 23시 발표분
    prev = adjusted - datetime.timedelta(days=1)
    return prev.strftime('%Y%m%d'), '2300'


def _fetch_kma(report_date: datetime.date) -> dict | None:
    """기상청 단기예보 API로 명일(report_date+1) 기상 조회"""
    from django.conf import settings
    api_key = getattr(settings, 'KMA_API_KEY', '').strip()
    if not api_key:
        return None

    tomorrow_str = (report_date + datetime.timedelta(days=1)).strftime('%Y%m%d')
    base_date, base_time = _kma_base_time(datetime.datetime.now())

    params = urllib.parse.urlencode({
        'serviceKey': api_key,
        'pageNo': 1,
        'numOfRows': 1000,
        'dataType': 'JSON',
        'base_date': base_date,
        'base_time': base_time,
        'nx': _KMA_NX,
        'ny': _KMA_NY,
    })
    url = (
        'https://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst'
        f'?{params}'
    )

    try:
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read())

        items = data['response']['body']['items']['item']
        temp_min = temp_max = None
        pop_list = []

        for item in items:
            if item['fcstDate'] != tomorrow_str:
                continue
            cat, val = item['category'], item['fcstValue']
            if cat == 'TMN':
                temp_min = round(float(val))
            elif cat == 'TMX':
                temp_max = round(float(val))
            elif cat == 'POP':
                try:
                    pop_list.append(int(val))
                except (ValueError, TypeError):
                    pass

        if temp_min is not None and temp_max is not None:
            return {
                'temp_min': temp_min,
                'temp_max': temp_max,
                'rain_pct': max(pop_list) if pop_list else 0,
                'source': '기상청',
            }
    except Exception:
        pass

    return None


def _fetch_openmeteo(report_date: datetime.date) -> dict | None:
    """Open-Meteo API 폴백"""
    date_str = (report_date + datetime.timedelta(days=1)).isoformat()
    url = (
        'https://api.open-meteo.com/v1/forecast'
        f'?latitude={_LAT}&longitude={_LON}'
        '&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max'
        '&timezone=Asia%2FSeoul'
        f'&start_date={date_str}&end_date={date_str}'
    )
    try:
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read())
        daily = data['daily']
        return {
            'temp_min': round(daily['temperature_2m_min'][0]),
            'temp_max': round(daily['temperature_2m_max'][0]),
            'rain_pct': int(daily['precipitation_probability_max'][0]),
            'source': 'Open-Meteo',
        }
    except Exception:
        return None


def fetch_tomorrow_weather(report_date: datetime.date) -> dict | None:
    """
    명일(report_date+1) 기상예보 반환.
    반환: {'temp_min': int, 'temp_max': int, 'rain_pct': int, 'source': str}
    실패 시 None. 결과는 1시간 메모리 캐시.
    """
    now = time.monotonic()
    cached = _cache.get(report_date)
    if cached:
        result, cached_at = cached
        if now - cached_at < _CACHE_TTL:
            return result

    result = _fetch_kma(report_date) or _fetch_openmeteo(report_date)
    if result:
        _cache[report_date] = (result, now)
    return result
