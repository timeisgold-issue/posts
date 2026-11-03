# 시간은 금이다 — 인스타 카드뉴스 자동 게시

@timeisgold_issue 카드뉴스를 예약 시간에 맞춰 인스타그램에 올리는 저장소예요.

## 폴더
- `queue/` 올릴 차례를 기다리는 게시물
- `published/` 올라간 게시물 (`result.json`에 인스타 주소)
- `failed/` 실패한 게시물 (`result.json`에 이유). 고친 뒤 `queue/`로 옮기면 다시 시도해요.

게시물 폴더 하나 = 카드뉴스 한 편:
```
queue/20261105-0730_bukhan-hacker/
  1.jpg ~ 6.jpg   1080x1350, 2~10장
  caption.txt     본문 (해시태그 5개까지)
  post.json       {"publish_at": "2026-11-05T07:30:00+09:00", "approved": true}
```
`approved`가 `true`인 것만 올라가요.

## 작동 방식
깃허브가 15분마다 `publish.py`를 실행해서 시간이 된 게시물을 올려요.
(깃허브 사정으로 몇 분~몇십 분 늦게 올라갈 수 있어요.)
Actions 탭 → "인스타 자동 게시" → Run workflow 로 바로 실행할 수 있어요. "토큰 연결만 확인" 체크를 켜두면 게시 없이 연결만 확인해요.

## 필요한 비밀값
Settings → Secrets and variables → Actions 에 넣어요.
- `IG_ACCESS_TOKEN` 인스타 업로드 토큰 (메타 통합 로그인 시스템 사용자 토큰, 만료 없음)
- `IG_USER_ID` (선택) 인스타 계정 번호. 비워두면 토큰으로 자동으로 찾아요.
