"""보고서에 넣을 품목과 기준을 정하는 곳.

각 품목:
  name     : 보고서에 보일 이름
  cat      : 채소 / 과일 / 특작 (탭 구분용)
  mid      : API의 상품 중분류명 (정확히 같아야 합니다. 예: 배추, 사과, 풋고추)
  small    : (선택) 상품 소분류명에 이 글자가 들어간 것만 (예: 풋고추 중 '청양')
  exclude  : (선택) 소분류명에 이 글자가 들어간 것은 뺍니다 (예: 밤 중 '생율'). '수입'은 모든 품목에서 뺍니다
  unit_kg  : 보고서에 보일 기준 포장 단위(kg). 가격은 kg당으로 계산한 뒤 이 단위로 환산합니다.
             None 이면 그날 가장 많이 거래된 포장 단위를 씁니다
  grade    : 기준 등급. None 이면 그날 거래량이 가장 많은 등급을 기준으로 씁니다
  art      : 카드 배경 일러스트 파일 이름 (docs/art/ 안)

처음 실행하면 data/catalog.json 에 API에 실제로 나오는 품목 이름이 모두 기록됩니다.
보고서에 '거래 기록이 없어요'로 나오는 품목은 그 파일을 보고 mid / small 을 고쳐 주세요.
"""

ITEMS = [
    # 채소 (unit_kg 가 None 이면 그날 가장 많이 거래된 포장 단위를 기준으로 씁니다)
    {"name": "배추", "cat": "채소", "mid": "배추", "unit_kg": 10, "grade": None, "art": "cabbage"},
    {"name": "무", "cat": "채소", "mid": "무", "unit_kg": 20, "grade": None, "art": "radish"},
    {"name": "양배추", "cat": "채소", "mid": "양배추", "unit_kg": 8, "grade": None, "art": "napacabbage"},
    {"name": "대파", "cat": "채소", "mid": "대파", "unit_kg": 1, "grade": None, "art": "greenonion"},
    {"name": "쪽파", "cat": "채소", "mid": "쪽파", "unit_kg": None, "grade": None, "art": "chive"},
    {"name": "양파", "cat": "채소", "mid": "양파", "unit_kg": 15, "grade": None, "art": "onion"},
    {"name": "깐마늘", "cat": "채소", "mid": "마늘", "small": "깐마늘", "unit_kg": None, "grade": None, "art": "garlic"},
    {"name": "생강", "cat": "채소", "mid": "생강", "unit_kg": None, "grade": None, "art": "ginger"},
    {"name": "감자", "cat": "채소", "mid": "감자", "unit_kg": 20, "grade": None, "art": "potato"},
    {"name": "고구마", "cat": "채소", "mid": "고구마", "unit_kg": None, "grade": None, "art": "sweetpotato"},
    {"name": "당근", "cat": "채소", "mid": "당근", "unit_kg": 20, "grade": None, "art": "carrot"},
    {"name": "열무", "cat": "채소", "mid": "열무", "unit_kg": None, "grade": None, "art": "radish"},
    {"name": "오이", "cat": "채소", "mid": "오이", "unit_kg": 10, "grade": None, "art": "cucumber"},
    {"name": "애호박", "cat": "채소", "mid": "호박", "small": "애호박", "unit_kg": 8, "grade": None, "art": "zucchini"},
    {"name": "단호박", "cat": "채소", "mid": "호박", "small": "단호박", "unit_kg": None, "grade": None, "art": "zucchini"},
    {"name": "옥수수", "cat": "채소", "mid": "옥수수", "unit_kg": None, "grade": None, "art": "corn"},
    {"name": "가지", "cat": "채소", "mid": "가지", "exclude": ["건가지"], "unit_kg": None, "grade": None, "art": "eggplant"},
    {"name": "청양고추", "cat": "채소", "mid": "풋고추", "small": "청양", "unit_kg": 10, "grade": None, "art": "pepper"},
    {"name": "꽈리고추", "cat": "채소", "mid": "꽈리고추", "unit_kg": None, "grade": None, "art": "pepper"},
    {"name": "홍고추", "cat": "채소", "mid": "홍고추", "unit_kg": None, "grade": None, "art": "pepper"},
    {"name": "파프리카", "cat": "채소", "mid": "파프리카", "unit_kg": None, "grade": None, "art": "paprika"},
    {"name": "피망", "cat": "채소", "mid": "피망(단고추)", "unit_kg": None, "grade": None, "art": "paprika"},
    {"name": "브로콜리", "cat": "채소", "mid": "브로콜리(녹색꽃양배추)", "unit_kg": None, "grade": None, "art": "broccoli"},
    {"name": "상추", "cat": "채소", "mid": "상추", "unit_kg": None, "grade": None, "art": "lettuce"},
    {"name": "양상추", "cat": "채소", "mid": "양상추", "unit_kg": None, "grade": None, "art": "lettuce"},
    {"name": "시금치", "cat": "채소", "mid": "시금치", "unit_kg": None, "grade": None, "art": "spinach"},
    {"name": "깻잎", "cat": "채소", "mid": "깻잎", "unit_kg": None, "grade": None, "art": "perilla"},
    {"name": "부추", "cat": "채소", "mid": "부추", "unit_kg": None, "grade": None, "art": "chive"},
    {"name": "얼갈이배추", "cat": "채소", "mid": "얼갈이배추", "unit_kg": None, "grade": None, "art": "bokchoy"},
    {"name": "청경채", "cat": "채소", "mid": "청경채", "unit_kg": None, "grade": None, "art": "bokchoy"},
    {"name": "갓", "cat": "채소", "mid": "갓", "unit_kg": None, "grade": None, "art": "leaf"},
    {"name": "미나리", "cat": "채소", "mid": "미나리", "unit_kg": None, "grade": None, "art": "leaf"},
    {"name": "쑥갓", "cat": "채소", "mid": "쑥갓", "unit_kg": None, "grade": None, "art": "leaf"},
    {"name": "근대", "cat": "채소", "mid": "근대", "unit_kg": None, "grade": None, "art": "spinach"},
    {"name": "치커리", "cat": "채소", "mid": "치커리", "unit_kg": None, "grade": None, "art": "lettuce"},
    # 나물 (봄나물은 철이 아니면 '거래 없음'으로 보이다가 출하가 시작되면 채워져요)
    {"name": "취나물", "cat": "나물", "mid": "취나물", "unit_kg": None, "grade": None, "art": "sprout"},
    {"name": "참나물", "cat": "나물", "mid": "참나물", "unit_kg": None, "grade": None, "art": "sprout"},
    {"name": "두릅", "cat": "나물", "mid": "두릅", "unit_kg": None, "grade": None, "art": "sprout"},
    {"name": "냉이", "cat": "나물", "mid": "냉이", "unit_kg": None, "grade": None, "art": "leaf"},
    {"name": "달래", "cat": "나물", "mid": "달래", "unit_kg": None, "grade": None, "art": "chive"},
    {"name": "쑥", "cat": "나물", "mid": "쑥", "unit_kg": None, "grade": None, "art": "leaf"},
    {"name": "머위", "cat": "나물", "mid": "머위", "unit_kg": None, "grade": None, "art": "leaf"},
    {"name": "고들빼기", "cat": "나물", "mid": "고들빼기", "unit_kg": None, "grade": None, "art": "leaf"},
    # 버섯
    {"name": "표고버섯", "cat": "버섯", "mid": "표고버섯", "small": "일반", "unit_kg": None, "grade": None, "art": "shiitake"},
    {"name": "새송이버섯", "cat": "버섯", "mid": "새송이버섯", "unit_kg": None, "grade": None, "art": "kingoyster"},
    {"name": "느타리버섯", "cat": "버섯", "mid": "느타리버섯", "unit_kg": None, "grade": None, "art": "kingoyster"},
    {"name": "팽이버섯", "cat": "버섯", "mid": "팽이버섯", "unit_kg": None, "grade": None, "art": "enoki"},
    {"name": "양송이", "cat": "버섯", "mid": "양송이", "unit_kg": None, "grade": None, "art": "shiitake"},
    # 과일
    {"name": "사과", "cat": "과일", "mid": "사과", "unit_kg": 10, "grade": None, "art": "apple"},
    {"name": "배", "cat": "과일", "mid": "배", "unit_kg": 15, "grade": None, "art": "pear"},
    {"name": "감귤", "cat": "과일", "mid": "감귤", "unit_kg": 5, "grade": None, "art": "tangerine"},
    {"name": "만감(한라봉 등)", "cat": "과일", "mid": "만감", "unit_kg": None, "grade": None, "art": "hallabong"},
    {"name": "단감", "cat": "과일", "mid": "단감", "unit_kg": 10, "grade": None, "art": "persimmon"},
    {"name": "대봉감", "cat": "과일", "mid": "떫은감", "small": "대봉", "unit_kg": None, "grade": None, "art": "persimmon"},
    {"name": "딸기", "cat": "과일", "mid": "딸기", "unit_kg": 2, "grade": None, "art": "strawberry"},
    {"name": "토마토", "cat": "과일", "mid": "토마토", "unit_kg": 5, "grade": None, "art": "tomato"},
    {"name": "방울토마토", "cat": "과일", "mid": "방울토마토", "unit_kg": None, "grade": None, "art": "cherrytomato"},
    {"name": "포도", "cat": "과일", "mid": "포도", "unit_kg": None, "grade": None, "art": "grape"},
    {"name": "키위", "cat": "과일", "mid": "참다래(키위)", "unit_kg": None, "grade": None, "art": "kiwi"},
    {"name": "참외", "cat": "과일", "mid": "참외", "unit_kg": None, "grade": None, "art": "melon"},
    {"name": "복숭아", "cat": "과일", "mid": "복숭아", "unit_kg": None, "grade": None, "art": "peach"},
    {"name": "자두", "cat": "과일", "mid": "자두", "unit_kg": None, "grade": None, "art": "plum"},
    {"name": "블루베리", "cat": "과일", "mid": "블루베리", "unit_kg": None, "grade": None, "art": "blueberry"},
    {"name": "수박", "cat": "과일", "mid": "수박", "unit_kg": None, "grade": None, "art": "watermelon"},
    {"name": "멜론", "cat": "과일", "mid": "멜론", "unit_kg": None, "grade": None, "art": "melon"},
    # 특작 (춘희네 품목)
    {"name": "밤", "cat": "특작", "mid": "밤", "exclude": ["생율"], "unit_kg": 4, "grade": None, "art": "chestnut"},
    {"name": "건고사리", "cat": "특작", "mid": "고사리", "small": "건고사리", "unit_kg": 1, "grade": None, "art": "fern"},
    {"name": "생고사리", "cat": "특작", "mid": "고사리", "small": "생고사리", "unit_kg": 1, "grade": None, "art": "fern"},
    {"name": "곶감", "cat": "특작", "mid": "곶감", "exclude": ["감말랭이"], "unit_kg": None, "grade": None, "art": "persimmon"},
    {"name": "매실", "cat": "특작", "mid": "매실", "unit_kg": 10, "grade": None, "art": "plum"},
]

# 시장별 비교 그래프에 보여줄 품목 (춘희네 주력 품목)
FEATURED = "밤"

# 등급 이름이 시장마다 달라서, 보고서에는 이 순서로 정렬해 보여줍니다. 없는 이름은 뒤로 갑니다.
GRADE_ORDER = ["특", "특품", "상", "상품", "보통", "중", "중품", "하", "하품", "등외"]

# 등급 이름이 비어 있거나 기호뿐인 거래는 이 이름으로 묶습니다
NO_GRADE = "등급 미표기"

# 보고서에 쓰는 품목 분류(탭) 순서
CATS = ["채소", "나물", "버섯", "과일", "특작"]

# ── 내 설정 ──────────────────────────────────────────────
# 카톡 카드와 보고서 맨 위에 크게 보여줄 '내 품목', 출하를 고민하는 '내 시장', 내 산지.
MY = {
    "items": ["밤", "건고사리", "생고사리", "매실", "곶감", "대봉감"],
    "markets": ["진주", "부산엄궁", "부산반여", "대구북부", "서울가락", "인천남촌"],
    "origin": "하동",          # 출하자 주소에 이 글자가 들어간 거래를 '내 산지'로 봅니다
    # 손에 쥐는 금액 추정: 경락가 - 위탁수수료 - 운송비
    "commission": 0.07,        # 도매법인 위탁수수료 비율 (청과 상한 7% 기준. 실제 요율로 바꾸세요)
    "freight": {},             # 시장별 운송비 원/kg, 예: {"진주": 40, "서울가락": 120}. 비워 두면 수수료만 뺍니다
}

# 거래량이 이보다 적은 품목(기준 등급, kg)은 등락 순위·요약에서 빼고 '물량 적음'으로 표시합니다
THIN_KG = 1000

# 몇 시까지 기다렸다가, 정산이 덜 끝났어도 그대로 보낼지 (한국 시간, 시)
SEND_DEADLINE_HOUR = 11

# 보고서 주소 (GitHub Pages)
SITE_URL = "https://roastedchestnut24-maker.github.io/sise-bot/"
