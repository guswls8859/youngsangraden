"""용산어린이정원 휴관/개관 여부 조회.

공식 안내 페이지(https://yongsanparkstory.kr/type1_visit_info)에 '오늘' 휴관 여부가
서버 렌더링으로 들어 있다:
    개관일: 오늘은 <b class="green">개관일</b>입니다.
    휴관일: 오늘은 <b class="red">휴관일</b>입니다.
이 한 줄을 파싱해 오늘 휴관인지 판별한다. 로그인·IP 제한 없이 일반 HTTP로 접근 가능.

GODATA 자동수집은 개관일에만 수행하기 위해 사용한다(휴관일이면 스킵).
"""
import logging
import re
import time

import requests

logger = logging.getLogger(__name__)

VISIT_INFO_URL = 'https://yongsanparkstory.kr/type1_visit_info'
_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 '
       '(KHTML, like Gecko) Chrome/120 Safari/537.36')
_STATUS_RE = re.compile(r'오늘은\s*<b class="(\w+)">\s*([^<]+?)\s*</b>\s*입니다')

# 메모리 캐시: (is_closed, cached_at). 당일 상태는 자주 안 바뀌므로 1시간 TTL.
_cache = None
_CACHE_TTL = 3600


def _fetch_is_closed():
    resp = requests.get(VISIT_INFO_URL, headers={'User-Agent': _UA}, timeout=(5, 15))
    resp.raise_for_status()
    m = _STATUS_RE.search(resp.text)
    if not m:
        raise ValueError('휴관/개관 표시를 찾지 못했습니다 (페이지 구조 변경 가능).')
    cls, label = m.group(1).lower(), m.group(2).strip()
    # 라벨 우선, 없으면 색(class)으로 판별 (red=휴관, green=개관)
    if label == '휴관일' or (label not in ('개관일', '휴관일') and cls == 'red'):
        return True
    return False


def is_closed_today(use_cache=True):
    """오늘 휴관이면 True, 개관이면 False, 판별 실패 시 None.

    None 은 '알 수 없음' — 호출측은 보통 수집을 진행(fail-open)하도록 처리한다.
    """
    global _cache
    if use_cache and _cache and (time.time() - _cache[1] < _CACHE_TTL):
        return _cache[0]
    try:
        closed = _fetch_is_closed()
    except Exception as e:
        logger.warning('휴관 여부 조회 실패: %s', e)
        return None
    _cache = (closed, time.time())
    logger.info('용산어린이정원 오늘 상태: %s', '휴관' if closed else '개관')
    return closed
