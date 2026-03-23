"""무신사 스냅 AI 시각 분석 스크립트
- 좋아요 순 상위 스냅 선별
- Claude Vision으로 패션 요소 분석
- 트렌드 리포트 생성
"""
import json
import base64
import os
import sys
from pathlib import Path
from datetime import date

# Anthropic API
import anthropic

DATA_DIR = Path(__file__).parent.parent / "data"

ANALYSIS_PROMPT = """이 패션 스냅 사진을 분석해주세요. 다음 항목을 JSON으로 응답해주세요:

{
  "overall_style": "전체 스타일 (예: 캐주얼, 스트릿, 미니멀, 아메카지 등)",
  "season_fit": "계절감 (봄/여름/가을/겨울/간절기)",
  "silhouette": "실루엣 (오버핏/레귤러/슬림 등)",
  "color_palette": ["주요 컬러 목록"],
  "color_mood": "컬러 무드 (모노톤/뉴트럴/비비드/파스텔 등)",
  "top": {"item": "상의 아이템명", "color": "색상", "fit": "핏"},
  "bottom": {"item": "하의 아이템명", "color": "색상", "fit": "핏"},
  "outer": {"item": "아우터 아이템명 또는 null", "color": "색상", "fit": "핏"},
  "shoes": {"item": "신발 종류", "color": "색상"},
  "accessories": ["액세서리 목록"],
  "key_items": ["이 코디의 핵심 아이템들"],
  "styling_tip": "이 코디의 포인트 한 줄 설명",
  "body_type_note": "172cm/78kg 체형에 적합한지 간단 코멘트"
}

JSON만 응답해주세요. 마크다운 코드블록 없이 순수 JSON만."""

REPORT_PROMPT = """다음은 최근 수집한 남성 패션 스냅 {count}개의 AI 분석 결과입니다.

{analyses}

위 데이터를 종합해서 다음 형식의 패션 트렌드 리포트를 작성해주세요:

## 📊 패션 트렌드 리포트 ({date})

### 1. 핵심 요약 (3줄)
이번 시기 남성 패션의 핵심 흐름을 3줄로 요약

### 2. 컬러 트렌드
- 가장 많이 보이는 컬러 조합
- 컬러 무드 경향

### 3. 아이템 트렌드
- 상의: 많이 보이는 아이템
- 하의: 많이 보이는 아이템
- 아우터: 많이 보이는 아이템
- 신발: 많이 보이는 아이템
- 주목할 아이템

### 4. 핏 & 실루엣
- 전체적인 핏 경향 (오버핏 vs 슬림핏 비율 등)
- 주류 실루엣

### 5. 스타일 키워드
- 가장 많이 보이는 스타일 유형

### 6. 🧍 체형 맞춤 추천 (172cm / 78kg)
- 이번 트렌드에서 잘 어울릴 아이템/조합
- 피해야 할 아이템/조합
- 추천 코디 3개

### 7. 주목 브랜드 & 태그
- 자주 등장한 브랜드/태그

리포트는 한국어로, 실용적이고 구체적으로 작성해주세요."""


def select_top_snaps(metadata_path, top_n=20):
    """좋아요 순 상위 스냅 선별"""
    with open(metadata_path) as f:
        data = json.load(f)
    
    snaps = data["snaps"]
    ranked = sorted(snaps, key=lambda x: x["like_count"], reverse=True)
    return ranked[:top_n]


def load_image_base64(image_path):
    """이미지를 base64로 로드"""
    with open(image_path, "rb") as f:
        return base64.standard_b64encode(f.read()).decode("utf-8")


def analyze_single_snap(client, snap, images_dir):
    """단일 스냅 이미지 분석"""
    snap_id = snap["id"]
    # 첫 번째 이미지 사용
    img_file = images_dir / f"{snap_id}_0.jpg"
    
    if not img_file.exists():
        print(f"  [SKIP] Image not found: {img_file.name}")
        return None
    
    img_b64 = load_image_base64(img_file)
    
    try:
        response = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": img_b64
                        }
                    },
                    {
                        "type": "text",
                        "text": ANALYSIS_PROMPT
                    }
                ]
            }]
        )
        
        result_text = response.content[0].text.strip()
        # JSON 파싱 시도
        try:
            result = json.loads(result_text)
        except json.JSONDecodeError:
            # 코드블록 제거 시도
            if "```" in result_text:
                result_text = result_text.split("```")[1]
                if result_text.startswith("json"):
                    result_text = result_text[4:]
                result = json.loads(result_text.strip())
            else:
                result = {"raw": result_text}
        
        result["snap_id"] = snap_id
        result["like_count"] = snap["like_count"]
        result["tags"] = snap["tags"]
        result["height"] = snap["height"]
        result["weight"] = snap["weight"]
        
        return result
    
    except Exception as e:
        print(f"  [ERROR] Analysis failed for {snap_id}: {e}")
        return None


def generate_report(client, analyses, report_date):
    """트렌드 리포트 생성"""
    analyses_text = json.dumps(analyses, ensure_ascii=False, indent=2)
    
    prompt = REPORT_PROMPT.format(
        count=len(analyses),
        analyses=analyses_text,
        date=report_date
    )
    
    response = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}]
    )
    
    return response.content[0].text


def main():
    today = date.today().isoformat()
    collection_dir = DATA_DIR / "snaps" / today
    images_dir = collection_dir / "images"
    metadata_path = collection_dir / "metadata.json"
    
    if not metadata_path.exists():
        print(f"[ERROR] No metadata found at {metadata_path}")
        sys.exit(1)
    
    # API 키 확인
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        # openclaw 설정에서 가져오기 시도
        config_path = Path.home() / ".openclaw" / "openclaw.json"
        if config_path.exists():
            with open(config_path) as f:
                config = json.load(f)
            # API 키는 환경변수에서 가져와야 함
        print("[ERROR] ANTHROPIC_API_KEY not set")
        sys.exit(1)
    
    client = anthropic.Anthropic(api_key=api_key)
    
    print(f"=== 패션 스냅 AI 분석 시작 ({today}) ===\n")
    
    # 1. 상위 스냅 선별
    print("[STEP 1] Selecting top snaps...")
    top_snaps = select_top_snaps(metadata_path, top_n=20)
    print(f"Selected {len(top_snaps)} snaps for analysis\n")
    
    # 2. 개별 이미지 분석
    print("[STEP 2] Analyzing images...")
    analyses = []
    for i, snap in enumerate(top_snaps):
        print(f"  [{i+1}/{len(top_snaps)}] Snap {snap['id']} (likes: {snap['like_count']})")
        result = analyze_single_snap(client, snap, images_dir)
        if result:
            analyses.append(result)
    
    print(f"\nAnalyzed {len(analyses)} / {len(top_snaps)} snaps\n")
    
    # 3. 분석 결과 저장
    analysis_path = collection_dir / "analysis.json"
    with open(analysis_path, "w", encoding="utf-8") as f:
        json.dump({
            "analyzed_at": today,
            "total_analyzed": len(analyses),
            "analyses": analyses
        }, f, ensure_ascii=False, indent=2)
    print(f"[SAVE] Analysis saved to {analysis_path}\n")
    
    # 4. 트렌드 리포트 생성
    print("[STEP 3] Generating trend report...")
    report = generate_report(client, analyses, today)
    
    report_path = collection_dir / "report.md"
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"[SAVE] Report saved to {report_path}\n")
    
    print("=== 분석 완료 ===")
    print(f"\nReport preview:\n{'='*50}")
    print(report[:2000])


if __name__ == "__main__":
    main()
