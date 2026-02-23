import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import json
from datetime import datetime

def scrape_gs25_event_goods():
    print("GS25 행사 상품 수집을 시작합니다...")
    
    # 오늘 날짜 구하기 (파일명 생성용: 예 - 260223)
    now = datetime.now()
    file_date_str = now.strftime("%y%m%d")
    
    # 1. 세션 생성 및 메인 페이지에서 CSRF 토큰 가져오기
    session = requests.Session()
    main_url = "http://gs25.gsretail.com/gscvs/ko/products/event-goods"
    
    # 서버 차단을 방지하기 위한 User-Agent 헤더 추가
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    response = session.get(main_url, headers=headers)
    response.raise_for_status()
    
    soup = BeautifulSoup(response.text, 'html.parser')
    csrf_input = soup.find('input', {'name': 'CSRFToken'})
    
    if not csrf_input:
        print("CSRF 토큰을 찾을 수 없습니다. 사이트 구조가 변경되었을 수 있습니다.")
        return
        
    csrf_token = csrf_input['value']
    print(f"보안 토큰 확보 완료: {csrf_token[:10]}...")
    
    # 2. API를 통해 데이터 수집 준비
    api_url = f"http://gs25.gsretail.com/gscvs/ko/products/event-goods-search?CSRFToken={csrf_token}"
    
    gs25_data_list = []
    page_num = 1
    page_size = 100 # 한 번에 가져올 상품 수
    
    while True:
        print(f" - {page_num}페이지 수집 중...")
        payload = {
            'pageNum': page_num,
            'pageSize': page_size,
            'searchType': '',
            'searchWord': '',
            'parameterList': 'TOTAL' # 전체 행사 상품
        }
        
        # API 요청
        res = session.get(api_url, params=payload, headers=headers)
        res.raise_for_status()
        
        data = res.json()
        
        # GS25 서버가 문자열(str)로 응답을 준 경우 딕셔너리로 변환
        if isinstance(data, str):
            data = json.loads(data)
            
        results = data.get('results', [])
        
        # 더 이상 수집할 결과가 없으면 반복문 종료
        if not results:
            break
            
        # 3. JSON 데이터에서 필요한 항목 추출 및 정제
        for item in results:
            # 행사 타입 변환
            event_code = item.get('eventTypeSp', {}).get('code', '')
            event_name = event_code
            if event_code == 'ONE_TO_ONE':
                event_name = '1+1'
            elif event_code == 'TWO_TO_ONE':
                event_name = '2+1'
            elif event_code == 'GIFT':
                event_name = '덤증정'
                
            # 가격 데이터 정수형 변환
            try:
                price = int(float(item.get('price', 0)))
            except ValueError:
                price = 0
                
            # 내부 데이터에서는 date 컬럼 제외하고 수집
            gs25_data_list.append({
                'brand': 'GS25',
                'name': item.get('goodsNm', '').strip(),
                'price': price,
                'event': event_name,
                'img_url': item.get('attFileNm', '')
            })
        
        # 다음 페이지
        page_num += 1
        
        # 서버 부하 방지 대기
        time.sleep(1) 
        
    # 4. 데이터프레임 변환 및 CSV 저장
    if gs25_data_list:
        df = pd.DataFrame(gs25_data_list)
        
        # 요청하신 파일명 형식: 편의점명_날짜.csv (예: GS25_260223.csv)
        csv_filename = f'GS25_{file_date_str}.csv'
        
        # 한글 깨짐 방지를 위해 utf-8-sig 인코딩 사용, index 제외
        df.to_csv(csv_filename, index=False, encoding='utf-8-sig')
        print(f"\n🎉 수집 완료! 총 {len(df)}개의 데이터가 '{csv_filename}' 파일로 저장되었습니다.")
        
        # 수집된 데이터 상위 5개 미리보기
        print("\n[수집된 데이터 미리보기]")
        print(df.head())
    else:
        print("\n수집된 데이터가 없습니다.")

if __name__ == "__main__":
    scrape_gs25_event_goods()