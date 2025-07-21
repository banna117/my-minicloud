# 🧱 My MiniCloud (Week 1)

## 🎯 프로젝트 개요
간단한 REST API 기반 클라우드 자원 할당 시스템입니다.  
사용자가 HTTP 요청을 통해 Docker 컨테이너를 생성하고,  
상태를 확인하고, 종료할 수 있는 미니 클라우드 플랫폼입니다.
---

## 📂 프로젝트 구조
my-minicloud/
├── app/
│   ├── __init__.py
│   ├── routes/
│   │   └── resource.py         # API 라우팅
│   ├── services/
│   │   └── docker_service.py   # Docker 실행/중단 로직
│   ├── utils/
│   │   └── state.py            # 상태 기록 유틸
├── resource_state.json         # 자원 상태 저장소
├── run.py                      # Flask 실행 엔트리포인트
├── requirements.txt
├── README.md                   # 💡 문서화 파일

---

## 🛠 실행 방법

```bash
pip install -r requirements.txt
python run.py

---

## ✅ 지원 기능 (Week 1)

- [x] `POST /resources` : 컨테이너 자원 생성
- [x] `GET /resources` : 전체 자원 조회 + 필터링 (user, tag, status)
- [x] `DELETE /resources/:id` : 자원 종료
- [x] 메타데이터 저장 (user, tag, 생성시각)
- [x] 상태 기록 (resource_state.json)

- 컨테이너 기반 자원 할당의 구조와 원리를 실제 구현


