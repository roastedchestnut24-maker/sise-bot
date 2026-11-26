"""카카오톡 '나에게 보내기'로 오늘 보고서를 보냅니다.

필요한 GitHub Secrets
  KAKAO_REST_KEY       : 카카오 개발자 앱의 REST API 키
  KAKAO_REFRESH_TOKEN  : 처음 한 번 'kakao-setup' 워크플로로 받아 저장합니다
  KAKAO_CLIENT_SECRET  : 앱에서 Client Secret 을 켠 경우에만

refresh token 은 두 달 동안 쓸 수 있고, 만료가 한 달 이내로 남으면 카카오가 새 토큰을 줍니다.
새 토큰을 받으면 .new_refresh_token 파일에 적어 두고, 워크플로가 그 값으로 Secret 을 바꿔 둡니다.
"""
import json
import os
from pathlib import Path

import requests

TOKEN_URL = "https://kauth.kakao.com/oauth/token"
MEMO_URL = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
REDIRECT_URI = "https://localhost:3000"
ROOT = Path(__file__).resolve().parent.parent


def _env(name, required=True):
    v = os.environ.get(name, "").strip()
    if required and not v:
        raise RuntimeError(f"{name} 가 설정되지 않았어요. README 의 카카오 설정 단계를 확인해 주세요.")
    return v


def _client():
    data = {"client_id": _env("KAKAO_REST_KEY")}
    secret = _env("KAKAO_CLIENT_SECRET", required=False)
    if secret:
        data["client_secret"] = secret
    return data


def authorize_url():
    return (f"https://kauth.kakao.com/oauth/authorize?client_id={_env('KAKAO_REST_KEY')}"
            f"&redirect_uri={REDIRECT_URI}&response_type=code&scope=talk_message")


def exchange_code(code):
    """처음 한 번: 로그인 후 받은 code → refresh token."""
    r = requests.post(TOKEN_URL, data={**_client(), "grant_type": "authorization_code",
                                       "redirect_uri": REDIRECT_URI, "code": code.strip()}, timeout=20)
    body = r.json()
    if "refresh_token" not in body:
        raise RuntimeError(f"토큰 발급 실패: {body.get('error_description') or body}")
    (ROOT / ".new_refresh_token").write_text(body["refresh_token"], encoding="utf-8")
    print("refresh token 을 받았어요. 워크플로가 Secret 에 저장합니다.")


def access_token():
    r = requests.post(TOKEN_URL, data={**_client(), "grant_type": "refresh_token",
                                       "refresh_token": _env("KAKAO_REFRESH_TOKEN")}, timeout=20)
    body = r.json()
    if "access_token" not in body:
        raise RuntimeError(f"카카오 토큰 갱신 실패: {body.get('error_description') or body}. "
                           f"refresh token 이 만료됐다면 kakao-setup 워크플로를 다시 실행해 주세요.")
    if body.get("refresh_token"):
        (ROOT / ".new_refresh_token").write_text(body["refresh_token"], encoding="utf-8")
        print("새 refresh token 을 받았어요. 워크플로가 Secret 을 갱신합니다.")
    return body["access_token"]


def send_report(summary, card_url, report_url, image_ok=True):
    link = {"web_url": report_url, "mobile_web_url": report_url}
    if image_ok:
        template = {
            "object_type": "feed",
            "content": {
                "title": summary["title"],
                "description": summary["description"],
                "image_url": card_url,
                "image_width": 800,
                "image_height": 800,
                "link": link,
            },
            "buttons": [{"title": "전체 리포트 보기", "link": link}],
        }
    else:
        template = {
            "object_type": "text",
            "text": f"{summary['title']}\n{summary['description']}",
            "link": link,
            "button_title": "전체 리포트 보기",
        }
    r = requests.post(MEMO_URL, headers={"Authorization": f"Bearer {access_token()}"},
                      data={"template_object": json.dumps(template, ensure_ascii=False)}, timeout=20)
    body = r.json()
    if body.get("result_code") != 0:
        raise RuntimeError(f"카톡 발송 실패: {body}. 보고서 주소의 도메인이 카카오 앱의 Web 플랫폼에 등록됐는지 확인해 주세요.")
    print("카톡을 보냈어요.")
