# GitHub Actions를 이용한 CI/CD 자동화 가이드

본 문서는 `Main API`와 `P2PNet API` 리포지토리에 코드가 푸시될 때, 자동으로 각각의 EC2 서버(CPU/GPU)에 배포되도록 설정하는 방법을 안내합니다.

---

## 🏗️ 기본 개념

### 1. `deploy.yml` (워크플로우 파일)
*   GitHub에게 "언제", "무엇을", "어떻게" 할지 알려주는 지시서입니다.
*   **위치**: 리포지토리의 `.github/workflows/` 폴더 안에 생성해야 합니다.
*   **역할**: `main` 브랜치에 코드가 올라오면 -> AWS 서버에 SSH로 접속해서 -> `git pull` 받고 -> 서버를 재시작해라!

### 2. GitHub Secrets (보안 변수)
*   서버 IP, SSH 키(pem 파일 내용)와 같이 공개되면 안 되는 정보를 안전하게 저장하는 금고입니다.
*   `yml` 파일 안에서 `${{ secrets.변수명 }}` 형태로 꺼내 씁니다.

---

## 🚀 1단계: GitHub Secrets 등록 (공통)

각 리포지토리마다 아래 과정을 수행하여 서버 접속 정보를 등록해야 합니다.

1.  GitHub 리포지토리 접속 > **Settings** > **Secrets and variables** > **Actions** > **New repository secret** 클릭
2.  아래 변수들을 각각 등록합니다.

| Secret 이름 | 내용 (Value) | 설명 |
| :--- | :--- | :--- |
| `EC2_HOST` | `x.x.x.x` | 대상 EC2 서버의 **퍼블릭 IP** |
| `EC2_USERNAME` | `ubuntu` | EC2 접속 계정 (Ubuntu AMI 기본값) |
| `EC2_SSH_KEY` | `-----BEGIN RSA...` | **key.pem 파일의 전체 내용** (텍스트로 열어서 복붙) |

> **주의**: `Main API` 레포에는 **Server A (CPU)**의 IP를, `P2PNet API` 레포에는 **Server B (GPU)**의 IP를 등록해야 합니다!

---

## 📁 2단계: 워크플로우 파일 생성

### Case A: Main API (Server A - CPU)

1.  `likeyou_final_mainapi` 프로젝트 루트에 폴더 생성: `.github/workflows/`
2.  파일 생성: `.github/workflows/deploy.yml`
3.  아래 내용 붙여넣기:

```yaml
name: Deploy Main API to Server A

on:
  push:
    branches: [ "main" ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH Remote Commands
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USERNAME }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            echo "🚀 배포 시작: Main API (CPU Server)"
            
            # 1. 프로젝트 폴더로 이동
            cd /home/ubuntu/main-api
            
            # 2. 최신 코드 받기
            git pull origin main
            
            # 3. 가상환경 활성화 및 패키지 설치 (필요 시)
            source venv/bin/activate
            pip install -r requirements.txt
            
            # 4. 서버 재시작 (PM2)
            # ecosystem.config.js에 정의된 모든 앱(m2, m4, m5) 재시작
            pm2 reload ecosystem.config.js
            
            echo "✅ 배포 완료!"
```

### Case B: P2PNet API (Server B - GPU)

1.  `likeyou_final_p2pnet` 프로젝트 루트에 폴더 생성: `.github/workflows/`
2.  파일 생성: `.github/workflows/deploy.yml`
3.  아래 내용 붙여넣기:

```yaml
name: Deploy P2PNet API to Server B (GPU)

on:
  push:
    branches: [ "main" ]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - name: SSH Remote Commands
        uses: appleboy/ssh-action@v1.0.0
        with:
          host: ${{ secrets.EC2_HOST }}
          username: ${{ secrets.EC2_USERNAME }}
          key: ${{ secrets.EC2_SSH_KEY }}
          script: |
            echo "🚀 배포 시작: P2PNet API (GPU Server)"
            
            # 1. 프로젝트 폴더로 이동
            cd /home/ubuntu/p2pnet-api
            
            # 2. 최신 코드 받기
            git pull origin main
            
            # 3. 가상환경 활성화 및 패키지 설치
            # GPU 서버는 Conda 환경을 사용할 수 있으므로 경로 주의
            # (방법 1) venv 사용 시
            # source venv/bin/activate
            
            # (방법 2) Conda 사용 시 (Server B 세팅에 따라 선택)
            # source /home/ubuntu/anaconda3/etc/profile.d/conda.sh
            # conda activate p2pnet
            
            # 패키지 업데이트
            # cd m3
            # pip install -r requirements.txt
            
            # 4. 서버 재시작 (PM2)
            # Server B에는 'm3-gpu'라는 이름으로 PM2 프로세스가 등록되어 있어야 함
            pm2 reload m3-gpu
            
            echo "✅ 배포 완료!"
```

---

## ✅ 3단계: 확인 방법

1.  로컬에서 코드 수정 후 `git push origin main`
2.  GitHub 리포지토리 페이지 상단 **Actions** 탭 클릭
3.  `Deploy ...` 워크플로우가 **초록색 체크(Success)**가 뜨는지 확인
4.  실제 서버(EC2)에서 `pm2 list` 또는 `pm2 logs`로 재시작되었는지 확인

---

## 💡 트러블슈팅 (자주 나는 에러)

1.  **`Host key verification failed`**:
    *   GitHub Action 서버가 우리 EC2를 처음 봐서 그렇습니다. `appleboy/ssh-action`은 이를 자동으로 처리해주지만, 혹시 안 되면 `script` 실행 전에 `ssh-keyscan` 단계가 필요할 수 있습니다. (위 설정은 보통 자동 처리됨)

2.  **`Permission denied`**:
    *   `EC2_SSH_KEY` 내용을 복사할 때 `-----BEGIN RSA PRIVATE KEY-----` 부터 `-----END RSA PRIVATE KEY-----` 까지 **줄바꿈 포함해서 정확히** 복사했는지 확인하세요.

3.  **`pm2: command not found`**:
    *   배포 스크립트 실행 시 `PATH` 문제일 수 있습니다.
    *   해결책: 스크립트 맨 위에 `export PATH=$PATH:/home/ubuntu/.nvm/versions/node/v.../bin` 처럼 경로를 잡아주거나, PM2 설치 시 `sudo npm install -g pm2`로 전역 설치했는지 확인하세요.

