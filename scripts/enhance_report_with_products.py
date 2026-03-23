#!/usr/bin/env python3
"""
패션 리포트에 실제 상품 정보 추가 스크립트
수집된 메타데이터의 goods 정보를 활용해서 구체적인 제품명과 브랜드 정보를 추가
"""

import json
import re
from collections import Counter

def extract_product_info_from_metadata(metadata_path):
    """메타데이터에서 인기 상품 정보 추출"""
    
    with open(metadata_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # 좋아요 순으로 정렬하여 상위 20개 스냅 선별
    snaps = sorted(data['snaps'], key=lambda x: x['like_count'], reverse=True)[:20]
    
    product_recommendations = {
        "상의": [],
        "하의": [],
        "아우터": [],
        "신발": [],
        "액세서리": []
    }
    
    brand_analysis = Counter()
    
    for snap in snaps:
        tags = snap.get('tags', [])
        goods = snap.get('goods', [])
        like_count = snap['like_count']
        
        # 브랜드 분석 (태그에서 브랜드명 추출)
        brand_tags = [tag for tag in tags if any(keyword in tag.lower() 
                     for keyword in ['무신사', '지오다노', '베리베인', '247', '고마츠', 
                                   '어반디타입', '커즈넬로', '제로', 'xero', 'wobo', 
                                   '워크온바디오프', '유니버스가먼트', '굿라이프웍스',
                                   '후러브스아트', '레테르코모', '데시레드', '인더스트'])]
        
        for brand in brand_tags:
            brand_analysis[brand] += like_count
            
        # 카테고리별 상품 분류
        if goods:
            goods_info = {
                'goods_no': goods[0]['goods_no'],
                'platform': goods[0]['platform'],
                'like_count': like_count,
                'tags': tags,
                'snap_id': snap['id']
            }
            
            # 태그 기반 카테고리 분류
            if any(keyword in ' '.join(tags).lower() for keyword in 
                  ['니트', '맨투맨', '스웨트', '카디건', '셔츠', '티셔츠', '폴로']):
                product_recommendations["상의"].append(goods_info)
            elif any(keyword in ' '.join(tags).lower() for keyword in 
                    ['팬츠', '바지', '치노', '슬랙스', '데님', '진']):
                product_recommendations["하의"].append(goods_info)
            elif any(keyword in ' '.join(tags).lower() for keyword in 
                    ['재킷', '코트', '아우터', '가디건', '집업', '블루종']):
                product_recommendations["아우터"].append(goods_info)
            elif any(keyword in ' '.join(tags).lower() for keyword in 
                    ['부츠', '로퍼', '스니커즈', '신발']):
                product_recommendations["신발"].append(goods_info)
            elif any(keyword in ' '.join(tags).lower() for keyword in 
                    ['모자', '캡', '가방', '팔찌', '시계', '벨트']):
                product_recommendations["액세서리"].append(goods_info)
    
    return product_recommendations, dict(brand_analysis.most_common(10))

def generate_product_section():
    """상품 추천 섹션 생성"""
    
    # 메타데이터에서 상품 정보 추출
    product_data, brand_data = extract_product_info_from_metadata('data/snaps/2026-03-22/metadata.json')
    
    section = """
## 8. 🛍️ 실제 상품 추천 (무신사 기준)

### 📦 체형별 추천 상품 (172cm/78kg)

#### 👔 상의 TOP 추천
"""
    
    # 상의 추천 (좋아요 순 상위 3개)
    top_tops = sorted(product_data["상의"], key=lambda x: x['like_count'], reverse=True)[:3]
    
    for i, item in enumerate(top_tops, 1):
        brand = next((tag for tag in item['tags'] if tag in ['무신사스탠다드', '베리베인', '지오다노', '247', 'WOBO']), '브랜드명')
        item_type = next((tag for tag in item['tags'] if tag in ['니트', '맨투맨', '카디건', '셔츠', '폴로']), '상의')
        
        section += f"""
**{i}. {brand} {item_type}**
- 상품번호: {item['goods_no']}
- 인기도: ❤️ {item['like_count']:,}개
- 무신사 링크: https://www.musinsa.com/app/goods/{item['goods_no']}
- 추천 이유: 172/78 체형에 적합한 릴랙스드 핏, 레이어링 활용도 높음
"""

    section += "\n#### 👖 하의 TOP 추천\n"
    
    # 하의 추천
    top_bottoms = sorted(product_data["하의"], key=lambda x: x['like_count'], reverse=True)[:3]
    
    for i, item in enumerate(top_bottoms, 1):
        brand = next((tag for tag in item['tags'] if tag in ['무신사스탠다드', '지오다노', '베리베인']), '브랜드명')
        item_type = next((tag for tag in item['tags'] if tag in ['치노팬츠', '와이드팬츠', '슬랙스', '데님']), '하의')
        
        section += f"""
**{i}. {brand} {item_type}**
- 상품번호: {item['goods_no']} 
- 인기도: ❤️ {item['like_count']:,}개
- 무신사 링크: https://www.musinsa.com/app/goods/{item['goods_no']}
- 추천 이유: 와이드 핏으로 허벅지 여유 확보, 다크/중간 톤으로 슬리밍 효과
"""

    section += "\n#### 🧥 아우터 TOP 추천\n"
    
    # 아우터 추천  
    top_outerwear = sorted(product_data["아우터"], key=lambda x: x['like_count'], reverse=True)[:2]
    
    for i, item in enumerate(top_outerwear, 1):
        brand = next((tag for tag in item['tags'] if tag in ['커즈넬로', '유니버스가먼트', '무신사']), '브랜드명')
        item_type = next((tag for tag in item['tags'] if tag in ['트렌치코트', '집업', '재킷', '가디건']), '아우터')
        
        section += f"""
**{i}. {brand} {item_type}**
- 상품번호: {item['goods_no']}
- 인기도: ❤️ {item['like_count']:,}개  
- 무신사 링크: https://www.musinsa.com/app/goods/{item['goods_no']}
- 추천 이유: 크롭/숏 기장으로 다리 비율 향상, 체형 커버 효과
"""

    section += f"""
### 🏷️ 인기 브랜드 순위 (좋아요 기준)

"""
    
    for i, (brand, score) in enumerate(list(brand_data.items())[:5], 1):
        section += f"{i}. **{brand}** (인기도: {score:,})\n"
    
    section += """
### 💡 구매 팁

#### 💰 가격대별 전략
- **3-5만원**: 무신사 스탠다드 베이직 아이템 (니트, 치노)
- **5-10만원**: 지오다노, 베리베인 시즌 아이템
- **10만원+**: 프리미엄 브랜드 시그니처 제품

#### 🛒 구매 우선순위 (172/78 체형)
1. **와이드 치노 팬츠** → 체형 커버의 기본
2. **릴랙스드 니트/맨투맨** → 상체 볼륨 자연스럽게 처리  
3. **크롭 기장 아우터** → 비율 보정의 핵심
4. **2-3cm 굽 있는 신발** → 자연스러운 키 보정

#### ⚠️ 구매 전 체크리스트
- [ ] 상의: 어깨선이 자연스럽게 떨어지는가?
- [ ] 하의: 허벅지 여유분 2-3cm 이상 확보했는가?
- [ ] 아우터: 기장이 엉덩이를 넘지 않는가?
- [ ] 전체: 상하 색상 밸런스가 적절한가?
"""
    
    return section

if __name__ == "__main__":
    print("상품 추천 섹션 생성 중...")
    product_section = generate_product_section()
    print("완료!")
    print("\n" + "="*50)
    print(product_section)