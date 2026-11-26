"""보고서에 넣을 품목과 기준을 정하는 곳.

각 품목:
  name     : 보고서에 보일 이름
  cat      : 채소 / 과일 / 특작 (탭 구분용)
  mid      : API의 상품 중분류명 (정확히 같아야 합니다. 예: 배추, 사과, 풋고추)
  small    : (선택) 상품 소분류명에 이 글자가 들어간 것만 (예: 풋고추 중 '청양')
  unit_kg  : 보고서에 보일 기준 포장 단위(kg). 가격은 kg당으로 계산한 뒤 이 단위로 환산합니다
  grade    : 기준 등급. None 이면 그날 거래량이 가장 많은 등급을 기준으로 씁니다
  art      : 카드 배경 일러스트 파일 이름 (docs/art/ 안)

처음 실행하면 data/catalog.json 에 API에 실제로 나오는 품목 이름이 모두 기록됩니다.
보고서에 '거래 기록이 없어요'로 나오는 품목은 그 파일을 보고 mid / small 을 고쳐 주세요.
"""

ITEMS = [
    # 채소
    {"name": "배추", "cat": "채소", "mid": "배추", "unit_kg": 10, "grade": None, "art": "cabbage"},
    {"name": "무", "cat": "채소", "mid": "무", "unit_kg": 20, "grade": None, "art": "radish"},
    {"name": "양배추", "cat": "채소", "mid": "양배추", "unit_kg": 8, "grade": None, "art": "napacabbage"},
    {"name": "대파", "cat": "채소", "mid": "대파", "unit_kg": 1, "grade": None, "art": "greenonion"},
    {"name": "양파", "cat": "채소", "mid": "양파", "unit_kg": 15, "grade": None, "art": "onion"},
    {"name": "감자", "cat": "채소", "mid": "감자", "unit_kg": 20, "grade": None, "art": "potato"},
    {"name": "당근", "cat": "채소", "mid": "당근", "unit_kg": 20, "grade": None, "art": "carrot"},
    {"name": "오이", "cat": "채소", "mid": "오이", "unit_kg": 10, "grade": None, "art": "cucumber"},
    {"name": "애호박", "cat": "채소", "mid": "호박", "small": "애호박", "unit_kg": 8, "grade": None, "art": "zucchini"},
    {"name": "청양고추", "cat": "채소", "mid": "풋고추", "small": "청양", "unit_kg": 10, "grade": None, "art": "pepper"},
    # 과일
    {"name": "사과", "cat": "과일", "mid": "사과", "unit_kg": 10, "grade": None, "art": "apple"},
    {"name": "배", "cat": "과일", "mid": "배", "unit_kg": 15, "grade": None, "art": "pear"},
    {"name": "감귤", "cat": "과일", "mid": "감귤", "unit_kg": 5, "grade": None, "art": "tangerine"},
    {"name": "단감", "cat": "과일", "mid": "단감", "unit_kg": 10, "grade": None, "art": "persimmon"},
    {"name": "딸기", "cat": "과일", "mid": "딸기", "unit_kg": 2, "grade": None, "art": "strawberry"},
    {"name": "토마토", "cat": "과일", "mid": "토마토", "unit_kg": 5, "grade": None, "art": "tomato"},
    # 특작
    {"name": "밤", "cat": "특작", "mid": "밤", "unit_kg": 4, "grade": None, "art": "chestnut"},
    {"name": "고사리", "cat": "특작", "mid": "고사리", "unit_kg": 1, "grade": None, "art": "fern"},
    {"name": "매실", "cat": "특작", "mid": "매실", "unit_kg": 10, "grade": None, "art": "apple"},
]

# 시장별 비교 그래프에 보여줄 품목 (춘희네 주력 품목)
FEATURED = "밤"

# 등급 이름이 시장마다 달라서, 보고서에는 이 순서로 정렬해 보여줍니다. 없는 이름은 뒤로 갑니다.
GRADE_ORDER = ["특", "특품", "상", "상품", "보통", "중", "중품", "하", "하품", "등외"]

# 보고서 주소 (GitHub Pages)
SITE_URL = "https://roastedchestnut24-maker.github.io/sise-bot/"
