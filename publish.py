"""
예약된 카드뉴스를 인스타그램에 자동으로 게시하는 프로그램.

queue/ 폴더 안의 게시물 폴더마다:
  1.jpg, 2.jpg, ... (최대 10장, 1080x1350 권장)
  caption.txt      (게시글 본문)
  post.json        {"publish_at": "2026-11-04T07:30:00+09:00", "approved": true}

publish_at 시간이 지났고 approved가 true인 게시물만 올린다.
성공하면 published/ 로, 실패하면 failed/ 로 옮기고 결과를 result.json에 남긴다.

필요한 깃허브 비밀값(Secrets):
  IG_ACCESS_TOKEN  인스타그램 업로드 토큰 (메타 '통합 로그인' 시스템 사용자 토큰)
  IG_USER_ID       (선택) 인스타 계정 번호. 없으면 토큰으로 자동으로 찾는다.

python3 publish.py --check   토큰이 잘 되는지만 확인 (게시하지 않음)
"""
import json
import os
import re
import shutil
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = os.environ.get("IG_API_BASE", "https://graph.facebook.com/v26.0")
HANDLE = "timeisgold_issue"
ROOT = Path(__file__).resolve().parent
QUEUE, DONE, FAILED = ROOT / "queue", ROOT / "published", ROOT / "failed"
REPO = os.environ.get("GITHUB_REPOSITORY", "timeisgold-issue/posts")
BRANCH = os.environ.get("GITHUB_REF_NAME", "main")


def api(method, path, **params):
    """인스타그램 API 호출. 오류가 나면 메시지와 함께 예외를 던진다."""
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    data = urllib.parse.urlencode(params).encode()
    url = f"{API}/{path}"
    if method == "GET":
        req = urllib.request.Request(f"{url}?{data.decode()}")
    else:
        req = urllib.request.Request(url, data=data, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"{method} {path} 실패: {e.code} {e.read().decode()[:500]}")


def wait_ready(container_id, label):
    """인스타가 이미지를 다 가져갈 때까지 기다린다 (최대 약 5분)."""
    for _ in range(30):
        status = api("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"{label} 처리 실패: {status}")
        time.sleep(10)
    raise RuntimeError(f"{label} 처리 시간 초과")


def raw_url(path: Path) -> str:
    rel = path.relative_to(ROOT).as_posix()
    return f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/{urllib.parse.quote(rel)}"


def find_user_id() -> str:
    """토큰에 연결된 인스타 계정 중 우리 계정 번호를 찾는다."""
    if os.environ.get("IG_USER_ID"):
        return os.environ["IG_USER_ID"]
    accounts = api("GET", "me/assigned_instagram_accounts", fields="id,username").get("data", [])
    for a in accounts:
        if a.get("username") == HANDLE:
            return a["id"]
    if len(accounts) == 1:
        return accounts[0]["id"]
    raise RuntimeError(f"토큰에 연결된 인스타 계정에서 {HANDLE}을 못 찾았어요: "
                       f"{[a.get('username') for a in accounts]}")


def check() -> int:
    user = find_user_id()
    info = api("GET", user, fields="username")
    limit = api("GET", f"{user}/content_publishing_limit", fields="quota_usage,config")
    print(f"연결 확인 완료: @{info.get('username')}")
    print(f"오늘 API로 올린 수 / 하루 한도: {json.dumps(limit.get('data', limit), ensure_ascii=False)}")
    prof = api("GET", user, fields="media_count")
    print(f"프로필 게시물 수(API 기준): {prof.get('media_count')}")
    media = api("GET", f"{user}/media", fields="permalink,timestamp,media_type", limit=10).get("data", [])
    for m in media:
        print(f"  {m.get('timestamp')} {m.get('media_type')} {m.get('permalink')}")
    return 0


def publish(folder: Path, user: str) -> dict:
    images = sorted(folder.glob("*.jpg"), key=lambda p: int(p.stem))
    if not 2 <= len(images) <= 10:
        raise RuntimeError(f"이미지는 2~10장이어야 해요 (지금 {len(images)}장)")
    caption = (folder / "caption.txt").read_text(encoding="utf-8").strip()
    tags = re.findall(r"#\S+", caption)
    if len(tags) > 5:
        raise RuntimeError(f"해시태그는 5개까지만 돼요 (지금 {len(tags)}개)")
    if len(caption) > 2200:
        raise RuntimeError(f"본문이 너무 길어요 ({len(caption)}자, 최대 2200자)")
    children = []
    for img in images:
        c = api("POST", f"{user}/media", image_url=raw_url(img), is_carousel_item="true")
        children.append(c["id"])
    for i, cid in enumerate(children, 1):
        wait_ready(cid, f"{i}번 이미지")

    carousel = api("POST", f"{user}/media", media_type="CAROUSEL",
                   children=",".join(children), caption=caption)
    wait_ready(carousel["id"], "카드뉴스 묶음")
    media = api("POST", f"{user}/media_publish", creation_id=carousel["id"])
    info = api("GET", media["id"], fields="permalink,timestamp")
    return {"media_id": media["id"], "permalink": info.get("permalink"),
            "timestamp": info.get("timestamp")}


def main():
    if not os.environ.get("IG_ACCESS_TOKEN"):
        print("토큰이 아직 설정되지 않았어요. 게시를 건너뜁니다.")
        return 0
    if "--check" in sys.argv:
        return check()
    now = datetime.now(timezone.utc)
    due = []
    for folder in sorted(p for p in QUEUE.glob("*") if p.is_dir()):
        meta = json.loads((folder / "post.json").read_text(encoding="utf-8"))
        if not meta.get("approved"):
            continue
        if datetime.fromisoformat(meta["publish_at"]) <= now:
            due.append(folder)
    if not due:
        print("올릴 시간이 된 게시물이 없어요.")
        return 0

    user = find_user_id()
    failed = 0
    for folder in due[:3]:  # 한 번에 최대 3편까지만 (몰아서 올라가지 않게)
        try:
            result = publish(folder, user)
            dest = DONE / folder.name
            print(f"게시 성공: {folder.name} → {result['permalink']}")
        except Exception as e:
            result = {"error": str(e)}
            dest = FAILED / folder.name
            failed += 1
            print(f"게시 실패: {folder.name} → {e}")
        result["finished_at"] = now.isoformat()
        dest.parent.mkdir(exist_ok=True)
        shutil.move(str(folder), str(dest))
        (dest / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
