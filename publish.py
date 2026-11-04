"""
예약된 카드뉴스를 인스타그램에 자동으로 게시하는 프로그램.

queue/ 폴더 안의 게시물 폴더마다:
  1.jpg, 2.mp4, 3.jpg ... (최대 10장, 1080x1350, 영상은 3~60초 H.264)
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


def wait_ready(container_id, label, tries=30):
    """인스타가 파일을 다 가져갈 때까지 기다린다 (기본 약 5분, 영상은 더 길게)."""
    for _ in range(tries):
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
    insights_report(user)
    return 0


def insights_report(user: str) -> None:
    """읽기 전용 진단: 팔로워 수, 계정 도달, 게시물별 조회·도달·저장·공유."""
    try:
        acc = api("GET", user, fields="followers_count,follows_count,media_count")
        print(f"팔로워 {acc.get('followers_count')} / 팔로잉 {acc.get('follows_count')} / 게시물 {acc.get('media_count')}")
    except Exception as e:
        print(f"계정 정보 조회 실패: {e}")
    for metric, extra in (("reach", {"period": "day"}), ("views", {"period": "day", "metric_type": "total_value"}),
                          ("accounts_engaged", {"period": "day", "metric_type": "total_value"})):
        try:
            r = api("GET", f"{user}/insights", metric=metric, **extra)
            print(f"계정 {metric}: {json.dumps(r.get('data', r), ensure_ascii=False)[:600]}")
        except Exception as e:
            print(f"계정 {metric} 조회 실패: {str(e)[:300]}")
    media = api("GET", f"{user}/media", fields="id,timestamp,permalink,like_count,comments_count", limit=25).get("data", [])
    print("게시물별 (시각 | 조회 | 도달 | 좋아요 | 댓글 | 저장 | 공유):")
    no_perm = False
    for m in media:
        vals = {}
        for metric in ("views", "reach", "saved", "shares"):
            if no_perm:
                vals[metric] = "권한없음"
                continue
            try:
                d = api("GET", f"{m['id']}/insights", metric=metric).get("data", [])
                vals[metric] = d[0]["values"][0]["value"] if d else "-"
            except Exception as e:
                no_perm = "(#10)" in str(e)
                vals[metric] = "권한없음" if no_perm else "오류"
        print(f"  {m.get('timestamp')} | {vals['views']} | {vals['reach']} | {m.get('like_count')} | "
              f"{m.get('comments_count')} | {vals['saved']} | {vals['shares']} | {m.get('permalink')}")


def media_files(folder: Path):
    """카드 순서대로 1.jpg, 2.mp4, 3.jpg ... (사진과 영상 섞기 가능)"""
    files = [p for p in folder.iterdir() if p.suffix.lower() in (".jpg", ".mp4") and p.stem.isdigit()]
    return sorted(files, key=lambda p: int(p.stem))


def make_child(user: str, path: Path) -> str:
    if path.suffix.lower() == ".mp4":
        c = api("POST", f"{user}/media", media_type="VIDEO", video_url=raw_url(path), is_carousel_item="true")
    else:
        c = api("POST", f"{user}/media", image_url=raw_url(path), is_carousel_item="true")
    return c["id"]


def publish(folder: Path, user: str) -> dict:
    items = media_files(folder)
    if not 2 <= len(items) <= 10:
        raise RuntimeError(f"카드는 2~10장이어야 해요 (지금 {len(items)}장)")
    caption = (folder / "caption.txt").read_text(encoding="utf-8").strip()
    tags = re.findall(r"#\S+", caption)
    if len(tags) > 5:
        raise RuntimeError(f"해시태그는 5개까지만 돼요 (지금 {len(tags)}개)")
    if len(caption) > 2200:
        raise RuntimeError(f"본문이 너무 길어요 ({len(caption)}자, 최대 2200자)")
    children = [(make_child(user, p), p) for p in items]
    for i, (cid, p) in enumerate(children, 1):
        is_video = p.suffix.lower() == ".mp4"
        wait_ready(cid, f"{i}번 {'영상' if is_video else '이미지'}", tries=60 if is_video else 30)

    carousel = api("POST", f"{user}/media", media_type="CAROUSEL",
                   children=",".join(cid for cid, _ in children), caption=caption)
    wait_ready(carousel["id"], "카드뉴스 묶음", tries=60)
    media = api("POST", f"{user}/media_publish", creation_id=carousel["id"])
    info = api("GET", media["id"], fields="permalink,timestamp")
    return {"media_id": media["id"], "permalink": info.get("permalink"),
            "timestamp": info.get("timestamp")}


def test_video() -> int:
    """영상 장이 인스타에서 처리되는지만 확인한다 (게시하지 않음, 묶음 컨테이너는 24시간 뒤 자동 폐기)."""
    user = find_user_id()
    path = ROOT / "tools" / "test_video.mp4"
    cid = make_child(user, path)
    wait_ready(cid, "시험 영상", tries=60)
    print(f"영상 처리 확인 완료 (게시 안 함): {path.name}")
    return 0


def main():
    if not os.environ.get("IG_ACCESS_TOKEN"):
        print("토큰이 아직 설정되지 않았어요. 게시를 건너뜁니다.")
        return 0
    if "--check" in sys.argv:
        return check()
    if "--test-video" in sys.argv:
        return test_video()
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
