# 매일 아침 농산물 시세 카톡 보고서

매일 아침 전국 공영도매시장 32곳의 전날 정산 가격을 받아서 인포그래픽 보고서(웹 페이지)와 카드 이미지를 만들고, 카카오톡 '나에게 보내기'로 보내 줍니다.

```
매일 05:40  GitHub Actions 자동 실행
   ↓  공공데이터포털 정산정보 API 에서 전날 시세 받기
   ↓  품목·등급별 kg당 가격, 전일 대비 등락, 7일 흐름 계산
   ↓  docs/ 에 보고서와 카드 이미지 저장 → GitHub Pages 로 공개
   ↓  카카오톡 '나에게 보내기'로 카드 이미지 + 링크 발송
```

## 비밀값 (Settings → Secrets and variables → Actions)

| 이름 | 넣을 값 |
|---|---|
| `DATA_GO_KR_KEY` | 공공데이터포털 일반 인증키 (Decoding) |
| `KAKAO_REST_KEY` | 카카오 개발자 앱의 REST API 키 |
| `GH_PAT` | GitHub 토큰 (Fine-grained, 이 저장소만, Secrets: Read and write) |
| `KAKAO_REFRESH_TOKEN` | 'Actions → 카카오 연결 (처음 한 번)' 이 자동으로 넣어 줍니다 |

## 처음 실행

1. Actions → 카카오 연결 (처음 한 번) → Run workflow (카카오 로그인 후 받은 code 붙여넣기)
2. Actions → 매일 시세 보고서 → Run workflow

## 품목 바꾸기

`sise/config.py` 의 `ITEMS` 에서 넣고 빼면 됩니다. `mid` 는 API의 상품 중분류명과 정확히 같아야 해요. 첫 실행 뒤 `data/catalog.json` 에 실제 이름이 기록됩니다.

## 알아두기

- 도매시장 정산 가격이라 소매 가격과 다릅니다.
- 등락은 품목마다 기준 등급 하나로만 비교합니다. 기준 등급을 비워 두면 그날 거래량이 가장 많은 등급을 씁니다.
- 포장 단위가 섞여 있어 모든 가격을 kg당으로 바꾼 뒤 기준 단위로 환산합니다. kg 단위가 아닌 거래는 빠집니다.
- 화면만 미리 보기: `python -m sise.run build --demo`
