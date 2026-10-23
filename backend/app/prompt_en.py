"""간단 모드 설명(한국어)을 ACE-Step 내장 LM용 영어 키워드로 변환.

0.6B LM은 한국어 설명을 거의 이해하지 못해 장르를 엉뚱하게 고르지만(예: "이별 발라드" → 밝은 J-pop),
영어 키워드를 주면 장르·분위기를 잘 따름. 외부 LLM 없이 음악 용어 사전으로 변환한다.
"""
import re

# (한국어 패턴, 영어) — 위에서부터 먼저 매칭. 긴 표현을 위에 둘 것.
TERMS: list[tuple[str, str]] = [
    # 장소/시간/날씨
    (r"비\s*(가\s*)?오는\s*날|비\s*내리는|빗속|장마", "rainy day"),
    (r"눈\s*(이\s*)?오는\s*날|눈\s*내리는|첫눈", "snowy day"),
    (r"새벽", "late night, dawn"), (r"한밤중|깊은\s*밤|밤", "night"), (r"아침", "morning"), (r"노을|해질녘", "sunset"),
    (r"봄", "spring"), (r"여름", "summer"), (r"가을", "autumn"), (r"겨울", "winter"), (r"크리스마스", "christmas"),
    (r"바닷가|해변|바다", "beach, ocean"), (r"드라이브", "night drive"), (r"도시", "city"), (r"카페", "cafe"),
    (r"우주", "space"), (r"숲", "forest"), (r"학교|청춘", "youth"), (r"졸업", "graduation"),
    # 장르
    (r"발라드", "ballad"), (r"케이\s*팝|k-?pop|아이돌", "k-pop"), (r"제이\s*팝", "j-pop"),
    (r"시티\s*팝", "city pop"), (r"로\s*파이|lo-?fi", "lo-fi"), (r"힙합|랩", "hip hop, rap"), (r"트랩", "trap"),
    (r"알앤비|r&b", "r&b"), (r"소울", "soul"), (r"재즈", "jazz"), (r"블루스", "blues"), (r"펑크(?!\s*록)", "funk"),
    (r"펑크\s*록|펑크록", "punk rock"), (r"하드\s*록|메탈", "hard rock, metal"), (r"록|락", "rock"),
    (r"인디", "indie"), (r"포크|어쿠스틱", "acoustic folk"), (r"컨트리", "country"), (r"트로트|뽕짝", "trot"),
    (r"이디엠|edm", "edm"), (r"하우스", "house"), (r"테크노", "techno"), (r"신스\s*팝|신스웨이브", "synthpop"),
    (r"일렉트로닉|전자\s*음악", "electronic"), (r"댄스", "dance"), (r"디스코", "disco"), (r"레게", "reggae"),
    (r"보사노바", "bossa nova"), (r"클래식|오케스트라", "orchestral, classical"),
    (r"뮤지컬", "musical theater"), (r"동요", "children's song"), (r"찬송가|가스펠", "gospel"),
    (r"게임\s*(ost|음악)|판타지", "epic fantasy game soundtrack"), (r"ost|사운드\s*트랙|영화\s*음악", "cinematic soundtrack"),
    (r"자장가", "lullaby"), (r"캐롤", "christmas carol"), (r"팝", "pop"),
    # 분위기/주제
    (r"이별|헤어진|헤어짐", "breakup, heartbreak"), (r"짝사랑", "unrequited love"), (r"첫사랑", "first love"),
    (r"사랑", "love"), (r"그리움|그리운|보고\s*싶", "longing"), (r"추억|회상", "nostalgic"),
    (r"슬픈|슬픔|우울", "sad, melancholic"), (r"외로운|외로움", "lonely"), (r"감성", "emotional"),
    (r"잔잔한|차분한|조용한", "calm, mellow"), (r"따뜻한|포근한", "warm"), (r"몽환적|꿈같은", "dreamy"),
    (r"신나는|흥겨운|경쾌한", "upbeat, energetic"), (r"밝은|행복한|기쁜", "bright, happy"),
    (r"웅장한|장엄한", "epic, grand"), (r"어두운|음산한", "dark"), (r"화난|분노|거친", "aggressive, angry"),
    (r"디스", "diss track"), (r"섹시한", "sensual"), (r"귀여운", "cute"), (r"희망", "hopeful"),
    (r"위로|응원", "comforting, uplifting"), (r"파티", "party"), (r"운동|헬스", "workout"), (r"공부|집중", "study, focus"),
    (r"레트로|복고|80년대", "retro 80s"), (r"90년대", "90s"),
    (r"느린|슬로우", "slow tempo"), (r"빠른", "fast tempo"),
    # 악기
    (r"피아노", "piano"), (r"통기타|어쿠스틱\s*기타", "acoustic guitar"), (r"일렉\s*기타|전자\s*기타", "electric guitar"),
    (r"기타", "guitar"), (r"베이스", "bass"), (r"드럼", "drums"), (r"바이올린", "violin"), (r"첼로", "cello"),
    (r"현악|스트링", "strings"), (r"색소폰", "saxophone"), (r"트럼펫", "trumpet"), (r"신디사이저|신스", "synthesizer"),
    (r"808", "808 bass"), (r"오르간", "organ"), (r"플루트", "flute"), (r"가야금", "gayageum"), (r"해금", "haegeum"),
    # 보컬
    (r"여성\s*보컬|여자\s*보컬|여자\s*목소리|여가수", "female vocal"),
    (r"남성\s*보컬|남자\s*보컬|남자\s*목소리|남가수", "male vocal"),
    (r"듀엣", "duet"), (r"합창", "choir"), (r"허스키", "husky vocal"), (r"고음", "powerful high notes"),
    (r"연주곡|보컬\s*없", "instrumental"),
]
_COMPILED = [(re.compile(p, re.IGNORECASE), en) for p, en in TERMS]

LANG_NAMES = {"ko": "Korean", "ja": "Japanese", "zh": "Chinese", "en": "English"}


def to_lm_query(description: str, vocal_language: str = "ko") -> str:
    """설명을 LM용 영어 쿼리로. 영어로 쓴 설명은 그대로 사용, 아는 단어가 없으면 원문 유지."""
    text = description.strip()
    if not re.search(r"[가-힣]", text):
        return text
    found: list[str] = []
    rest = text
    for pat, en in _COMPILED:
        if pat.search(rest):
            rest = pat.sub(" ", rest)  # 같은 부분이 다른 항목에 또 걸리지 않게 제거
            for term in en.split(", "):
                if term not in found:
                    found.append(term)
    if not found:
        return text
    lang = LANG_NAMES.get(vocal_language)
    head = [f"{lang} song"] if lang and vocal_language != "en" else []
    return ", ".join(head + found)
