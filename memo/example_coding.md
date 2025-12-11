# 💻 Spring Boot 연동 코드 예시 가이드

이 문서는 Spring Boot 개발자가 AI 모듈(FastAPI)과 연동하기 위해 필요한 **Controller**, **Service**, **Repository** 계층의 구현 예시를 담고 있습니다.

---

## 0. ⚙️ 사전 설정 (Configuration)

AI 서버와 HTTP 통신을 하기 위해 `RestTemplate`을 빈(Bean)으로 등록해야 합니다.

```java
@Configuration
public class AppConfig {
    @Bean
    public RestTemplate restTemplate() {
        return new RestTemplate();
    }
}
```

---

## 1. 🚧 M1: 도로 위험도 분석 (DB 조회 패턴)

M1은 API 호출 없이 **DB에서 직접 데이터를 조회**합니다.

### Entity
```java
@Entity
@Table(name = "COM_Location") // DB 테이블명
@Getter
public class ComLocation {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;
    
    private Integer hour;       // 시간대 (0~23)
    private Double riskScore;   // 위험도 (0.0 ~ 1.0)
    
    @Column(columnDefinition = "TEXT")
    private String geometry;    // 도로 좌표 정보 (GeoJSON)
}
```

### Service
```java
@Service
@RequiredArgsConstructor
public class RiskService {
    private final ComLocationRepository repository;

    /**
     * 특정 시간대의 도로 위험도 데이터 전체 조회
     * 요청: "지금(18시) 도로 상황 어때?"
     */
    public List<ComLocation> getRiskByHour(int hour) {
        // AI 서버 호출 없이 DB에서 바로 조회
        return repository.findByHour(hour);
    }
}
```

---

## 2. 🛡️ M2: 안심 경로 탐색 (실시간 API 패턴)

사용자의 요청을 받아 **AI 서버(8002 포트)**로 전달하고 응답을 반환합니다.

### DTO
```java
@Getter @Setter @AllArgsConstructor
public class RouteRequest {
    private Location origin;      // 출발지
    private Location destination; // 도착지
    
    @Getter @Setter @AllArgsConstructor
    public static class Location {
        private double lat;
        private double lng;
    }
}
```

### Service
```java
@Service
@RequiredArgsConstructor
public class RouteService {
    private final RestTemplate restTemplate;

    /**
     * 안심 경로 탐색 요청
     */
    public RouteResponse getSafeRoute(double startLat, double startLng, double endLat, double endLng) {
        String url = "http://localhost:8002/m2/route";
        
        // 요청 데이터 생성
        RouteRequest request = new RouteRequest(
            new RouteRequest.Location(startLat, startLng),
            new RouteRequest.Location(endLat, endLng)
        );

        // API 호출 (POST) 및 응답 반환
        return restTemplate.postForObject(url, request, RouteResponse.class);
    }
}
```

---

## 3. 👥 M3 & 🚨 M4: 제어 및 모니터링 (Control & Poll)

**제어(Start/Stop)**는 API로, **데이터 확인**은 DB 조회를 통해 수행합니다. (M3 예시)

### Controller
```java
@RestController
@RequestMapping("/api/crowd")
@RequiredArgsConstructor
public class CrowdController {
    private final CrowdService crowdService;

    // 1. [제어] 분석 시작 (관리자가 'CCTV 분석 시작' 버튼 클릭 시)
    @PostMapping("/start")
    public String startAnalysis(@RequestParam String cctvNo) {
        crowdService.startAiAnalysis(cctvNo);
        return "분석이 시작되었습니다.";
    }

    // 2. [모니터링] 실시간 현황 조회 (프론트엔드가 3초마다 폴링)
    @GetMapping("/status")
    public CrowdLog getRealtimeStatus(@RequestParam String cctvNo) {
        // AI 서버에 묻지 않고, DB에 쌓인 최신 로그를 가져옴
        return crowdService.getLatestLog(cctvNo);
    }
}
```

### Service
```java
@Service
@RequiredArgsConstructor
public class CrowdService {
    private final RestTemplate restTemplate;
    private final CrowdLogRepository repository;

    // AI 서버에게 "분석 시작해" 명령 (M3 Port: 8003)
    public void startAiAnalysis(String cctvNo) {
        String url = "http://localhost:8003/control/start?cctv_no=" + cctvNo;
        restTemplate.postForLocation(url, null);
    }

    // DB에서 가장 최신 분석 결과 1건 조회
    public CrowdLog getLatestLog(String cctvNo) {
        // SQL: SELECT * FROM DAT_Crowd_Detection WHERE cctv_no = ? ORDER BY detected_at DESC LIMIT 1
        return repository.findTopByCctvNoOrderByDetectedAtDesc(cctvNo);
    }
}
```

---

## 4. 🔮 M5: 사고 위험 예측 (Trigger & Read)

예측을 **실행(Trigger)**하는 API와 결과를 **조회(Read)**하는 로직이 분리됩니다.

### Service
```java
@Service
@RequiredArgsConstructor
public class PredictionService {
    private final RestTemplate restTemplate;
    private final PredictionRepository repository;

    // 1. [Trigger] 관리자가 시나리오 변경 시 예측 실행 요청 (M5 Port: 8005)
    public void runPrediction(String scenario) {
        String url = "http://localhost:8005/m5/predict";
        
        Map<String, Object> body = new HashMap<>();
        body.put("region_code", 26500800);
        body.put("target_date", "20251115"); // 가이드 고정 날짜
        body.put("scenario", scenario);      // "rainy", "sunny" 등

        // 결과는 DB에 저장되므로 리턴값은 크게 중요하지 않음 (성공 여부만 확인)
        restTemplate.postForObject(url, body, String.class);
    }

    // 2. [Read] 대시보드 차트용 데이터 조회
    public List<PredictionData> getPredictionResult(String date, String scenario) {
        // DB에 저장된 예측 결과 조회
        return repository.findByBaseDateAndScenarioType(date, scenario);
    }
}
```

