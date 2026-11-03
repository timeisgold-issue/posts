"""
완성된 카드 PNG 묶음을 게시 대기열(queue/)에 넣는 도우미.

python3 make_post.py <카드PNG폴더> <캡션파일> <게시시각> <이름>
  예) python3 make_post.py ~/v4/out_hack caption.txt "2026-11-05 07:30" bukhan-hacker

- PNG를 이름 앞 숫자 순서대로 1.jpg, 2.jpg ... 로 바꿔 저장 (JPEG 품질 95)
- 게시시각은 한국 시간 기준
- approved는 PD님 승인 후에만 true로 넣는다 (--approved)
"""
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    approved = "--approved" in sys.argv
    if len(args) != 4:
        print(__doc__)
        return 1
    src, caption_file, when, slug = Path(args[0]), Path(args[1]), args[2], args[3]
    at = datetime.strptime(when, "%Y-%m-%d %H:%M")
    pngs = sorted(src.glob("*.png"), key=lambda p: int(re.match(r"\d+", p.name).group()))
    if not 2 <= len(pngs) <= 10:
        raise SystemExit(f"카드는 2~10장이어야 해요 (지금 {len(pngs)}장)")

    dest = ROOT / "queue" / f"{at:%Y%m%d-%H%M}_{slug}"
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for i, p in enumerate(pngs, 1):
        img = Image.open(p).convert("RGB")
        if img.size != (1080, 1350):
            raise SystemExit(f"{p.name} 크기가 {img.size}예요 (1080x1350이어야 해요)")
        img.save(dest / f"{i}.jpg", "JPEG", quality=95, subsampling=0, optimize=True)
    shutil.copy(caption_file, dest / "caption.txt")
    meta = {"publish_at": at.strftime("%Y-%m-%dT%H:%M:00+09:00"), "approved": approved}
    (dest / "post.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"대기열에 넣었어요: {dest.relative_to(ROOT)} ({len(pngs)}장, 승인={approved})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
