"""무신사 스냅 수집 스크립트
- API로 스냅 데이터 수집 (남성 필터)
- 이미지 다운로드
- 메타데이터 JSON 저장
"""
import requests
import json
import os
import sys
from datetime import datetime, date
from pathlib import Path

BASE_URL = "https://content.musinsa.com/api2/content/snap/v1/rankings/DAILY"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Referer": "https://www.musinsa.com/snap/main/ranking/snap",
    "Accept": "application/json",
}

DATA_DIR = Path(__file__).parent.parent / "data"


def collect_snaps(gender="ALL", max_pages=5, page_size=20):
    """스냅 랭킹 데이터 수집"""
    all_snaps = []
    
    for page in range(1, max_pages + 1):
        url = f"{BASE_URL}?gender={gender}&page={page}&size={page_size}"
        resp = requests.get(url, headers=HEADERS, timeout=10)
        
        if resp.status_code != 200:
            print(f"[ERROR] Page {page}: status {resp.status_code}")
            break
        
        data = resp.json()
        snaps = data.get("data", {}).get("list", [])
        
        if not snaps:
            print(f"[INFO] Page {page}: no more data")
            break
        
        all_snaps.extend(snaps)
        print(f"[OK] Page {page}: {len(snaps)} snaps collected")
        
        # 다음 페이지 없으면 중단
        if not data.get("link", {}).get("next"):
            break
    
    return all_snaps


def filter_male_snaps(snaps):
    """남성 스냅만 필터링"""
    male_snaps = [s for s in snaps if s.get("model", {}).get("gender") == "MEN"]
    print(f"[FILTER] {len(snaps)} total → {len(male_snaps)} male snaps")
    return male_snaps


def download_images(snaps, output_dir):
    """스냅 이미지 다운로드"""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    downloaded = 0
    for snap in snaps:
        snap_id = snap["id"]
        medias = snap.get("medias", [])
        
        for i, media in enumerate(medias):
            if media["type"] != "IMAGE":
                continue
            
            img_url = media["path"]
            # 고화질로 요청
            img_url_hq = f"{img_url}?w=720"
            
            filename = f"{snap_id}_{i}.jpg"
            filepath = output_dir / filename
            
            if filepath.exists():
                continue
            
            try:
                img_resp = requests.get(img_url_hq, headers=HEADERS, timeout=10)
                if img_resp.status_code == 200:
                    filepath.write_bytes(img_resp.content)
                    downloaded += 1
            except Exception as e:
                print(f"[WARN] Failed to download {filename}: {e}")
    
    print(f"[DOWNLOAD] {downloaded} images saved to {output_dir}")
    return downloaded


def extract_metadata(snaps):
    """분석에 필요한 메타데이터 추출"""
    metadata = []
    for snap in snaps:
        meta = {
            "id": snap["id"],
            "gender": snap.get("model", {}).get("gender"),
            "height": snap.get("model", {}).get("height"),
            "weight": snap.get("model", {}).get("weight"),
            "skin_tone": snap.get("model", {}).get("skinTone"),
            "tags": [t["name"] for t in snap.get("tags", [])],
            "content": snap.get("detail", {}).get("content", ""),
            "like_count": snap.get("aggregations", {}).get("likeCount", 0),
            "view_count": snap.get("aggregations", {}).get("viewCount", 0),
            "comment_count": snap.get("aggregations", {}).get("commentCount", 0),
            "rank": snap.get("ranking", {}).get("rank"),
            "highlight": snap.get("ranking", {}).get("highlight"),
            "image_count": len([m for m in snap.get("medias", []) if m["type"] == "IMAGE"]),
            "images": [m["path"] for m in snap.get("medias", []) if m["type"] == "IMAGE"],
            "goods": [
                {"goods_no": g.get("goodsNo"), "platform": g.get("goodsPlatform")}
                for g in snap.get("goods", [])
            ],
            "displayed_from": snap.get("displayedFrom"),
        }
        metadata.append(meta)
    return metadata


def save_collection(metadata, collection_dir):
    """수집 결과 저장"""
    collection_dir = Path(collection_dir)
    collection_dir.mkdir(parents=True, exist_ok=True)
    
    meta_path = collection_dir / "metadata.json"
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump({
            "collected_at": datetime.now().isoformat(),
            "total_snaps": len(metadata),
            "snaps": metadata
        }, f, ensure_ascii=False, indent=2)
    
    print(f"[SAVE] Metadata saved to {meta_path}")
    return meta_path


def main():
    today = date.today().isoformat()
    collection_dir = DATA_DIR / "snaps" / today
    
    print(f"=== 무신사 스냅 수집 시작 ({today}) ===\n")
    
    # 1. 전체 스냅 수집 (ALL로 가져온 후 남성 필터)
    print("[STEP 1] Collecting snaps...")
    all_snaps = collect_snaps(gender="ALL", max_pages=5, page_size=20)
    print(f"Total collected: {len(all_snaps)}\n")
    
    if not all_snaps:
        print("[ERROR] No snaps collected. Exiting.")
        sys.exit(1)
    
    # 2. 남성 필터링 (ALL에서 남성만)
    # 참고: gender=MALE이 빈 결과를 반환하므로 ALL에서 필터
    print("[STEP 2] Filtering male snaps...")
    male_snaps = filter_male_snaps(all_snaps)
    
    # 남성 스냅이 너무 적으면 전체도 포함 (트렌드 파악용)
    if len(male_snaps) < 10:
        print(f"[INFO] Male snaps too few ({len(male_snaps)}), keeping all snaps for analysis")
        target_snaps = all_snaps
    else:
        target_snaps = male_snaps
    
    # 3. 메타데이터 추출
    print("\n[STEP 3] Extracting metadata...")
    metadata = extract_metadata(target_snaps)
    
    # 4. 이미지 다운로드
    print("\n[STEP 4] Downloading images...")
    img_dir = collection_dir / "images"
    download_images(target_snaps, img_dir)
    
    # 5. 저장
    print("\n[STEP 5] Saving collection...")
    save_collection(metadata, collection_dir)
    
    # 요약
    print(f"\n=== 수집 완료 ===")
    print(f"총 스냅: {len(metadata)}개")
    print(f"저장 위치: {collection_dir}")
    
    # 간단한 통계
    tags_all = []
    for m in metadata:
        tags_all.extend(m["tags"])
    
    from collections import Counter
    top_tags = Counter(tags_all).most_common(10)
    print(f"\n[TOP TAGS]")
    for tag, count in top_tags:
        print(f"  #{tag}: {count}")


if __name__ == "__main__":
    main()
