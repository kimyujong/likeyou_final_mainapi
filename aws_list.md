# AWS 단일 EC2 배포 체크리스트 (Bare Metal / Dockerless)

본 문서는 Docker 없이 **단일 EC2 인스턴스**에서 Main API(Python 3.10), P2PNet API(Python 3.8), Spring Boot 서버(Java 17)를 동시에 운영하기 위한 작업 순서입니다.

이 방식은 **"Bare Metal Deployment"** 또는 **"Native Process Deployment"**라고 부르며, 초기 인프라 복잡도를 낮추고 AI 모델의 오버헤드를 최소화하기에 적합합니다.

> **참고 자료 모음**
> *   [AWS 공식 문서: EC2 인스턴스에서 스왑 메모리 설정](https://repost.aws/ko/knowledge-center/ec2-memory-swap-file)
> *   [CodeChaCha: Ubuntu에 Python 특정 버전 설치 (PPA 활용)](https://codechacha.com/ko/ubuntu-install-python39/)
> *   [PM2 공식 문서: Ecosystem File 설정](https://pm2.keymetrics.io/docs/usage/application-declaration/)
> *   [Certbot: Nginx on Ubuntu 20.04/22.04](https://certbot.eff.org/instructions?ws=nginx&os=ubuntufocal)

## 1. 서버 아키텍처 및 포트 계획

**인프라 전략**: Modular Monolith on Single EC2 (Polyglot)

| 서비스 명 | 리포지토리 (Git) | 언어/버전 | 경로 | 내부 포트 | 비고 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Main API** | `likeyou_final_mainapi` | Python 3.10 | `/home/ubuntu/main-api` | `8005` (m5)<br>`8002` (m2)<br>`8004` (m4) | FastAPI (m1, m2, m4, m5 통합) |
| **P2PNet API** | `likeyou_final_p2pnet` | Python 3.8 | `/home/ubuntu/p2pnet-api` | `8003` | P2PNet (m3) 전용 |
| **Spring Boot** | `backend-springboot` | Java 17 | `/home/ubuntu/springboot` | `8080` | 메인 백엔드 |
| **Nginx** | - | - | - | `80`, `443` | 리버스 프록시 / SSL 인증 / 라우팅 |

---

## 2. EC2 인스턴스 초기 설정

### 2-1. 인스턴스 생성 및 접속
*   OS: **Ubuntu Server 22.04 LTS** (권장)
*   Instance Type: 최소 **t3.large** 권장 (AI 모델 2개 + Spring Boot 동시 구동)
*   Storage: 30GB 이상 (PyTorch, TensorFlow 라이브러리 및 모델 용량)

### 2-2. 필수 패키지 설치 및 Python 버전 관리
Ubuntu 22.04는 기본적으로 Python 3.10을 탑재하고 있습니다. P2PNet(m3) 구동을 위해 3.8 버전을 추가로 설치해야 합니다.

```bash
# 시스템 업데이트
sudo apt update && sudo apt upgrade -y

# 기본 도구 및 AWS CLI 설치
sudo apt install -y git curl unzip build-essential awscli

# Python 버전 관리를 위한 PPA 추가 (deadsnakes)
sudo add-apt-repository ppa:deadsnakes/ppa
sudo apt update

# Python 3.8 및 3.10 관련 패키지 설치 (venv, dev 필수)
sudo apt install -y python3.8 python3.8-venv python3.8-dev
sudo apt install -y python3.10 python3.10-venv python3.10-dev

# Java 17 설치 (Spring Boot 용)
sudo apt install -y openjdk-17-jdk
java -version  # 설치 확인
```

### 2-3. Swap 메모리 설정 (★필수★)
메모리 부족으로 AI 모델 로딩 중 서버가 다운되는 것을 방지하기 위해 반드시 설정합니다. (최소 4GB, 권장 8GB)

```bash
# 4GB 스왑 파일 생성
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# 재부팅 후에도 유지되도록 fstab 등록
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 확인
free -h
```

---

## 3. 애플리케이션 배포 (Git Clone)

### 3-1. 디렉토리 구조 생성
```bash
mkdir -p /home/ubuntu/main-api
mkdir -p /home/ubuntu/p2pnet-api
mkdir -p /home/ubuntu/springboot
```

### 3-2. Main API 배포 (Python 3.10)
*   **Repo**: `likeyou_final_mainapi`
*   **경로**: `/home/ubuntu/main-api`

```bash
# 1. Clone
git clone https://github.com/kimyujong/likeyou_final_mainapi.git /home/ubuntu/main-api

# 2. 가상환경 생성 (Python 3.10)
cd /home/ubuntu/main-api
python3.10 -m venv venv
source venv/bin/activate

# 3. 의존성 설치 (통합 requirements.txt 사용)
pip install -r requirements.txt

# 4. .env 파일 생성 (Supabase 키 설정)
vi .env
# SUPABASE_URL=...
# SUPABASE_KEY=...
```

### 3-3. P2PNet API 배포 (Python 3.8)
*   **Repo**: `likeyou_final_p2pnet`
*   **경로**: `/home/ubuntu/p2pnet-api`

```bash
# 1. Clone
git clone https://github.com/kimyujong/likeyou_final_p2pnet.git /home/ubuntu/p2pnet-api

# 2. 가상환경 생성 (Python 3.8)
cd /home/ubuntu/p2pnet-api
python3.8 -m venv venv
source venv/bin/activate

# 3. 의존성 설치
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
pip install -r requirements.txt
```

### 3-4. Spring Boot 배포
*   **경로**: `/home/ubuntu/springboot`
*   `.jar` 파일은 로컬 빌드 후 아래 "대용량 파일 업로드" 단계를 통해 업로드합니다.

### 3-5. 대용량 리소스 설정 (AWS S3 활용)
오토스케일링 및 서버 재구축 시 신속한 복구를 위해 모델 파일과 데이터를 **AWS S3**에 저장하고, 서버 부팅 시 다운로드하도록 구성합니다.

**Step 1: S3 버킷 준비 및 업로드 (내 PC에서 진행)**
1.  AWS Console > **S3** > **Create bucket** (예: `likeyou-models`)
2.  로컬에 있는 대용량 파일들을 버킷에 업로드합니다.
    *   나중에 관리를 위해 `m3`, `m4`, `m5`, `common` 등으로 폴더를 나누어 올리는 것을 권장합니다.
    *   예시 S3 구조:
        *   `s3://likeyou-models/m4/best.pt`
        *   `s3://likeyou-models/m5/saved_models/...`
        *   `s3://likeyou-models/m5/total_weather.xlsx`
        *   `s3://likeyou-models/m3/model/...`
        *   `s3://likeyou-models/jar/app.jar`

**Step 2: EC2에 S3 접근 권한 부여 (IAM Role)**
*Access Key를 서버에 저장하지 않는 보안 모범 사례(Best Practice)입니다.*

1.  AWS Console > **IAM** > **Roles** > **Create role**
2.  Trusted entity type: **AWS Service** > **EC2** 선택
3.  Permissions policies: **AmazonS3ReadOnlyAccess** 검색 및 체크
4.  Role Name: `EC2-S3-Access-Role` 입력 후 생성
5.  AWS Console > **EC2** > 인스턴스 선택 > **Actions** > **Security** > **Modify IAM role**
6.  방금 만든 Role 선택 후 **Update IAM role**

**Step 3: 서버에서 리소스 다운로드**
`/home/ubuntu/storage` 디렉토리에 모든 파일을 모읍니다. (사용자 .env 설정 기준)

```bash
# 1. 저장소 폴더 생성
mkdir -p /home/ubuntu/storage

# 2. S3에서 파일 다운로드 (cp 또는 sync 사용)
# S3 버킷명은 본인의 것으로 변경하세요.

# M4 모델
aws s3 cp s3://likeyou-models/m4/best.pt /home/ubuntu/storage/

# M5 모델 및 데이터
aws s3 cp s3://likeyou-models/m5/total_weather.xlsx /home/ubuntu/storage/
# 폴더(saved_models)는 recursive 옵션 필요. 
# 주의: S3 폴더 구조에 따라 /home/ubuntu/storage/saved_models/... 로 다운로드 됩니다.
# 만약 .env에서 M5_MODEL_DIR=/home/ubuntu/storage/ 라고 설정했다면 
# 실제 모델 파일들이 storage 바로 아래에 있어야 하는지, storage/saved_models 에 있어도 되는지 코드 확인 필요.
# 여기서는 storage 바로 아래에 모델 파일들을 풉니다.
aws s3 cp s3://likeyou-models/m5/saved_models/ /home/ubuntu/storage/ --recursive

# M1 데이터 (필요 시)
aws s3 cp s3://likeyou-models/m1/roads_cleaned_filtered.geojson /home/ubuntu/storage/

# Spring Boot Jar (별도 위치)
aws s3 cp s3://likeyou-models/jar/app.jar /home/ubuntu/springboot/app.jar
```

---

## 4. 프로세스 관리 (PM2 활용 - 자동 실행 설정)

Node.js 기반의 PM2를 사용하여 모든 프로세스(Python, Java)를 통합 관리하고, **서버 재부팅 시 자동으로 실행되도록 설정**합니다.

### 4-1. PM2 설치
```bash
# Node.js 설치
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt install -y nodejs

# PM2 설치
sudo npm install -g pm2
```

### 4-2. ecosystem.config.js 작성
홈 디렉토리(`/home/ubuntu`)에 생성. 이 설정 파일에 등록된 앱들은 PM2가 관리하며, `pm2 start` 명령어로 한 번에 켜집니다.

```javascript
// ecosystem.config.js
module.exports = {
  apps : [
    {
      name: "m5-predict",
      script: "/home/ubuntu/main-api/m5/server.py",
      interpreter: "/home/ubuntu/main-api/venv/bin/python",
      args: "",
      cwd: "/home/ubuntu/main-api", // Working Directory 중요
      env: { PORT: 8005, PYTHONPATH: "/home/ubuntu/main-api" }
    },
    {
      name: "m2-route",
      script: "/home/ubuntu/main-api/m2/server.py",
      interpreter: "/home/ubuntu/main-api/venv/bin/python",
      cwd: "/home/ubuntu/main-api",
      env: { PORT: 8002, PYTHONPATH: "/home/ubuntu/main-api" }
    },
    {
      name: "m4-fall",
      script: "/home/ubuntu/main-api/m4/server.py",
      interpreter: "/home/ubuntu/main-api/venv/bin/python",
      cwd: "/home/ubuntu/main-api",
      env: { PORT: 8004, PYTHONPATH: "/home/ubuntu/main-api" }
    },
    {
      name: "m3-p2pnet",
      script: "/home/ubuntu/p2pnet-api/m3/server.py",
      interpreter: "/home/ubuntu/p2pnet-api/venv/bin/python",
      cwd: "/home/ubuntu/p2pnet-api", // venv가 다르므로 주의
      env: { PORT: 8003, PYTHONPATH: "/home/ubuntu/p2pnet-api" }
    },
    {
      name: "springboot",
      script: "java",
      args: "-jar /home/ubuntu/springboot/app.jar",
      exec_interpreter: "none",
      exec_mode: "fork"
    }
  ]
}
```

### 4-3. 실행 및 부팅 시 자동 시작 등록
이 단계를 수행하면 EC2가 재부팅되어도 PM2가 알아서 위 앱들을 다시 실행시킵니다.

```bash
# 1. 설정 파일로 모든 서버 시작
pm2 start ecosystem.config.js

# 2. 현재 실행 중인 리스트 저장
pm2 save

# 3. 부팅 시 자동 실행 등록 (Startup Script 생성)
pm2 startup
# (주의) 위 명령어를 치면 터미널에 'sudo env PATH=...' 로 시작하는 명령어가 출력됩니다.
# 그 출력된 명령어를 그대로 복사해서 붙여넣고 엔터를 쳐야 설정이 완료됩니다.
```

---

## 5. Nginx & SSL 설정 (도메인 연결)

### 5-1. Nginx 설치
```bash
sudo apt install -y nginx
```

### 5-2. Certbot (SSL) 설치
HTTPS 적용을 위해 무료 인증서 도구인 Certbot을 설치합니다.

```bash
sudo apt install -y certbot python3-certbot-nginx
```

### 5-3. 도메인 설정 (Nginx Config)
`/etc/nginx/sites-available/likeyou` 파일 생성:

```nginx
# 1. 관리자 웹 (likeyousafety.cloud)
server {
    server_name likeyousafety.cloud;

    location / {
        # 관리자 프론트엔드 (정적 파일 또는 프록시)
        # root /var/www/admin;
        # index index.html;
        proxy_pass http://localhost:8080; # 임시로 백엔드 연결 예시
    }
}

# 2. 사용자 앱 & 백엔드 API (likeyousafe.cloud)
server {
    server_name likeyousafe.cloud;

    # 앱용 웹페이지
    location /app {
        # alias /var/www/mobile-app;
        proxy_pass http://localhost:8080/app; # Spring Boot가 앱 페이지를 서빙한다면
    }

    # API (Spring Boot)
    location /api {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
    
    # (선택) AI 서버 직접 호출이 필요할 경우 (보안 주의)
    # location /ai/m2 { proxy_pass http://localhost:8002; }
}
```

### 5-4. SSL 인증서 발급
Nginx 설정을 마치고 아래 명령어를 실행하면 자동으로 HTTPS 설정이 추가됩니다.

```bash
sudo ln -s /etc/nginx/sites-available/likeyou /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx

# 인증서 발급 (이메일 입력 등 절차 따르기)
sudo certbot --nginx -d likeyousafety.cloud -d likeyousafe.cloud
```
