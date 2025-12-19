# 🚀 최종 배포 체크리스트 (Final Deployment Checklist)

서버 3대(Front EC2, Server A, Server B)의 완벽한 연동을 위한 마지막 단계입니다.

## 1. Backend (Server A: Main & AI CPU) - Spring Boot
가장 먼저 백엔드 API 서버를 가동합니다.

- [ ] **[로컬] Spring Boot 코드 GitHub 업로드**
    - 프로젝트 루트에서 실행
    - `git add spiringboot`
    - `git commit -m "feat: Add Spring Boot application for deployment"`
    - `git push origin main`

- [ ] **[Server A] 코드 내려받기 및 빌드**
    - `git pull`
    - `cd spiringboot`
    - `chmod +x gradlew` (실행 권한 부여)
    - `./gradlew clean build -x test` (테스트 제외하고 빌드)

- [ ] **[Server A] 실행 및 PM2 등록**
    - **테스트 실행:** `java -jar build/libs/safety-0.0.1-SNAPSHOT.jar`
        - (로그에 `Started SafetyApplication` 뜨면 성공 -> Ctrl+C 로 종료)
    - **무중단 실행:** `pm2 start "java -jar build/libs/safety-0.0.1-SNAPSHOT.jar" --name "springboot-server"`
    - **저장:** `pm2 save`

## 2. Frontend (Front EC2: Web Server) - React
백엔드 주소를 바라보도록 설정하고 빌드하여 정적 파일을 올립니다.

- [ ] **[로컬] 환경 변수 설정**
    - `frontend/.env` 파일 생성 (없으면 새로 만들기)
    - 내용 작성:
      ```properties
      VITE_API_URL=https://api.likeyousafety.cloud
      ```

- [ ] **[로컬] 빌드 (Build)**
    - `cd frontend`
    - `npm run build`
    - **결과:** `frontend/dist` 폴더가 생성됨

- [ ] **[Front EC2] 배포 (Upload)**
    - **작업:** 로컬의 `frontend/dist` 폴더 안의 **모든 내용물**을 서버의 웹 루트 폴더로 업로드
    - **경로:** `/var/www/html/` (Nginx 기본 경로인 경우)
    - **도구:** FileZilla(추천) 또는 SCP 명령어 사용

## 3. Configuration Check (설정 점검)
- [ ] **[Server A] application.yaml 점검**
    - `m3` (Server B) URL이 Server B의 실제 IP 또는 도메인으로 설정되어 있는지 확인
    - `localhost:8003`으로 되어 있다면 Server A 내부 포워딩이 되어 있거나, Server B IP로 변경 필요

- [ ] **[Web] 최종 통합 테스트**
    - 브라우저로 `https://likeyousafety.cloud` 접속
    - **확인 1:** 지도가 정상적으로 뜨는가?
    - **확인 2:** 개발자 도구(F12) -> Network 탭 -> API 요청이 `https://api.likeyousafety.cloud/...` 로 전송되고 200 OK를 받는지 확인
