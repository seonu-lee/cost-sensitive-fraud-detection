# 노트북 사실관계 확인 요약 보고
> 최종 보고서 작성 전 Day 01~09 노트북 전체 독해 결과  
> 작성일: 2026-07-11

---

## Day 01 — 데이터 로딩 및 기초 탐색

### 데이터 현황
- `train_transaction`: 590,540행 × 394열 (메모리 2,062.07MB → 861.12MB, 58.2% 감소)
- `train_identity`: 144,233행 × 41열 (143.14MB → 16.17MB, 88.7% 감소)
- Left join 후: 590,540행 × 435열 (`has_identity` 포함)
- isFraud 비율: **3.499%** (사기 20,663건 / 정상 569,877건)
- 데이터 기간: 182일 (약 6.1개월)

### 주요 발견
- `has_identity=1` 거래의 사기 비율(7.85%)이 `has_identity=0`(2.09%)보다 **3.7배** 높음 → Day 2 통계 검증 대상
- V컬럼 339개 → 결측률 기준 **15개 그룹**으로 100% 정확히 분해 (패턴 일치도 100%)
- 결측률 구간별 컬럼 수: 0~1% (112개), 10~50% (108개), 50~90% (202개), 90%+ (12개)
- card1: 고유값 13,553개 (고카디널리티), card4: 4개(visa/mastercard/amex/discover)

### 저장
- `data/processed/day1_merged.parquet`

---

## Day 02 — 통계 검정 및 클래스 불균형

### 카이제곱 검정 (범주형 변수 vs isFraud)

| 변수 | chi2 | Cramér's V | 유의 |
|---|---|---|---|
| ProductCD | 16,742.17 | 0.1684 | True |
| has_identity | 10,683.64 | 0.1345 | True |
| card6 | 5,957.03 | 0.1006 | True |
| DeviceType | 609.62 | 0.0658 | True |
| card4 | 364.87 | 0.0249 | True |

### 결측 플래그 카이제곱 검정

| 변수 | chi2 | Cramér's V | 유의 |
|---|---|---|---|
| addr_missing | 15,016.72 | 0.1595 | True |
| has_identity | 10,683.64 | 0.1345 | True |
| M123_missing | 4,720.58 | 0.0894 | True |
| M789_missing | 2,876.27 | 0.0698 | True |

### V그룹 결측 플래그 검정
- 15개 그룹 중 12개 유의 (V_group1, V_group2, V_group3 제외 — Cramér's V < 0.004)

### 정규성 검정
- D'Agostino-Pearson + Anderson-Darling으로 C1~C14, TransactionAmt, D1 **전부 비정규** 확인
- Shapiro-Wilk (5,000건 샘플, 참고용), 5만 건 샘플링으로 주 검정 수행

### Mann-Whitney U 검정 (연속형 변수 vs isFraud)
- 효과크기 상위: C4(0.375), C8(0.366), C10(0.356), C12(0.327), C7(0.295)
- **TransactionAmt: p=0.226, effect_size=0.005 → 유의하지 않음**
- amt_zscore: p=4.51e-125, effect_size=0.099 → 유의
- C3: 유의하나 effect_size=0.004 (실질적 차이 미미)

### 클래스 불균형
- 비율: 1:27.6 (scale_pos_weight 권장값 27.58)
- 처리 결정: **class_weight/scale_pos_weight 채택** (SMOTE 보류)
  - 보류 근거: 사기 절대량 충분(20,663건), V컬럼 PCA 익명 변수에 SMOTE 보간 의미 불확실

### 저장
- `data/processed/day2_merged.parquet` (94.28 MB)

---

## Day 03 — Feature Engineering

### UID 설계
- **UID = card1 + card2 + addr1** (고유값 41,672개, 평균 14.17건/UID)
- D1 제외 이유: 거래마다 달라지는 timedelta 변수 (그룹화 부적합)
- card3·card5: 소수 값에 집중, card4·card6: 약한 신호, addr2: 88%가 단일값(87.0)

### 금액 편차 변수

| 변수 | effect_size_r | p_value |
|---|---|---|
| amt_zscore | 0.09930 | 4.51e-125 |
| **amt_robust_zscore** | **0.11573** | 9.67e-155 |
| amt_hour_robust_zscore | 0.00500 | 0.205 → **제외** |

- Robust Z-score 공식: `(x - median) / (1.4826 × MAD)`, MAD floor=0.3 채택 (결측 12.83%, std 3.88)
- MAD=0인 그룹: 21,612개 → floor 미적용 시 분모 폭발(min -214,942.55)

### V컬럼 차원 축소

| 항목 | 전 | 후 |
|---|---|---|
| V컬럼 전체 | 339개 | PCA 89개 주성분 (약 72% 감소) |
| V_group13+14 통합 | 22개 | 11개 주성분 (설명분산 0.917) |
| C컬럼군 | 11개 | 2개 주성분 (설명분산 0.974) |
| 결측 플래그 25개 | 25개 | AllFlag 9개 주성분 (설명분산 0.913) |

### 다중공선성 처리
- 초기 VIF 최댓값: 86,308 (V_group15_missing)
- 처리 후 VIF 최댓값: **572** (V_group2_PC1) — 99.3% 개선
- 완전 해소 불가 (전체 통합 시 해석 가능성 원칙과 충돌)

### 최종 피처
- day3_final.parquet: **208개** (모델 입력 203개), 결측치 0, 105.87 MB
- 시간 파생변수: Transaction_month(0~6), Transaction_weekday, Transaction_hour(D9와 완전 일치)

---

## Day 04 — CV 전략 및 모델 비교

### CV 전략 확정 과정
- GroupKFold → **StratifiedGroupKFold**로 교체
- 교체 이유: GroupKFold Fold 2의 사기 비율(2.87%)이 다른 fold(3.17~3.94%)보다 낮아 PR-AUC 왜곡
- 교체 후: 전체 fold 사기 비율 **0.0350으로 균등화**
- OOF(Out-of-Fold) 방식 채택: 590,540건 전체 순환 예측

### 전처리 방식 확정
- StandardScaler (MinMaxScaler 거부: 극단값 스케일 지배, RobustScaler 거부: 파생변수에 이미 적용)
- 타겟 인코딩: smoothing=20, fold 내부 적용 (LR/RF용)
- LightGBM/XGBoost: category 네이티브 처리

### 모델 비교 결과 (OOF, StratifiedGroupKFold 5-fold)

| 순위 | 모델 | PR-AUC (mean±std) | ROC-AUC (mean±std) |
|---|---|---|---|
| 1 | **Random Forest** | **0.4972 ± 0.0342** | **0.8632 ± 0.0089** |
| 2 | LightGBM | 0.4860 ± 0.0304 | 0.8463 ± 0.0114 |
| 3 | XGBoost | 0.4471 ± 0.0337 | 0.8101 ± 0.0169 |
| 4 | Logistic Regression | 0.3366 ± 0.0261 | 0.8235 ± 0.0182 |

### 저장
- `data/processed/day4_oof_results.pkl` (36.04 MB)

---

## Day 05 — 통계적 검증

### DeLong Test (ROC-AUC, Holm 다중비교 보정)
- 6개 쌍 전부 유의 (대표본 효과 주의: 59만 건)
- 순위: RF(0.8632) > LightGBM(0.8465) > LR(0.8229) > XGBoost(0.8099)
- RF vs LightGBM: z=11.67, p≈0 (유의)

| 쌍 | AUC_A | AUC_B | 차이 | z_stat | p_holm | 유의 |
|---|---|---|---|---|---|---|
| LR vs RF | 0.8229 | 0.8632 | -0.0403 | -28.08 | 0.0 | True |
| LR vs XGBoost | 0.8229 | 0.8099 | +0.0130 | 7.06 | 1.66e-12 | True |
| LR vs LightGBM | 0.8229 | 0.8465 | -0.0235 | -14.69 | 0.0 | True |
| RF vs XGBoost | 0.8632 | 0.8099 | +0.0533 | 31.80 | 0.0 | True |
| RF vs LightGBM | 0.8632 | 0.8465 | +0.0167 | 11.67 | 0.0 | True |
| XGBoost vs LightGBM | 0.8099 | 0.8465 | -0.0366 | -36.70 | 0.0 | True |

### Bootstrap CI (PR-AUC, 1,000회)
- 순위: RF(0.4971) > LightGBM(0.4848) > XGBoost(0.4449) > LR(0.3340)
- **RF vs LightGBM 차이: 0.0122, 95% CI [0.0089, 0.0158]** → 통계적 유의, 실질 차이 작음

### McNemar Test (threshold=0.5, Holm 보정)
- LR vs RF: LR만 맞힌 7,808건 vs RF만 맞힌 69,503건 (약 9배)
- RF vs LightGBM: RF만 맞힌 21,030건 vs LightGBM만 맞힌 6,081건 (약 3.5배)

### Calibration 분석

| 모델 | 평균 \|Gap\| | 방향 |
|---|---|---|
| Random Forest | 0.1366 | 과소신뢰 |
| XGBoost | 0.2485 | 과신뢰 |
| LightGBM | 0.3130 | 과신뢰 |
| Logistic Regression | 0.4007 | 과신뢰 |

### 저장
- `data/processed/day5_results.pkl`

---

## Day 06 — 하이퍼파라미터 튜닝

### LightGBM: Optuna 20 trials + Early Stopping
- PR-AUC: 0.4860 → **0.5101** (+0.0241)
- Best trial: 17번 (총 소요시간 62분 47초)
- `n_estimators=5000` (고정), `early_stopping_rounds=50`
- Pruner: MedianPruner(n_startup_trials=5, n_warmup_steps=2)

**Best params:**
```
learning_rate: 0.1563037874293778
num_leaves: 165
min_child_samples: 32
subsample: 0.9248534606596772
colsample_bytree: 0.6651160762107319
reg_lambda: 0.00025077983643406634
scale_pos_weight: 27.58 (고정)
```

### RF: OOB 기반 탐색
- Trial당 25분+ 소요로 Optuna 보류
- OOB 최고: max_depth=None, min_samples_leaf=2, max_features=0.5 (OOB=0.9812)
- ExtraTrees PR-AUC: 0.4912 (RF 기본값 0.4972 대비 -0.006) → RF 기본값 유지

### 최종 후보
| 모델 | PR-AUC |
|---|---|
| **LightGBM (튜닝)** | **0.5101** |
| RF (기본값) | 0.4972 |

### 저장
- `data/processed/day6_tuning_results.pkl`

---

## Day 07 — Calibration + Threshold Optimization

### Calibration 결과 (CalibratedClassifierCV, method='isotonic', cv=5)

| 기준 | LightGBM (최종 선택) | RF |
|---|---|---|
| PR-AUC | **0.5517 ± 0.0272** | 0.5100 ± 0.0339 |
| Calibration Gap | 0.1447 (53.7% 개선) | **0.0507** |
| Brier Score | 0.0241 | **0.0231** |

- LightGBM 보정 전: PR-AUC 0.5101, Gap 0.3130
- RF 보정 전: PR-AUC 0.4972, Gap 0.1366

### 최종 모델 선택
- **LightGBM 채택** (PR-AUC 우선 기준: 0.5517 > RF 0.5100)

### Threshold Optimization (비용 최소화)

FN 비용 근거: 사기 거래 TransactionAmt 중앙값 75.0, FP 비용 시나리오: 1, 3, 5, 10, 20, 30

**대표 시나리오 선택:**
- FN 기준: 중앙값(75.0), FP 비용: 10 → FN:FP = 7.5:1
- **최적 threshold: 0.20**

| 지표 | 값 |
|---|---|
| Precision | 0.4008 |
| Recall | 0.5608 |
| F1 | 0.4675 |
| FN (놓친 사기) | 9,076건 |
| FP (오탐) | 17,324건 |
| TN | 552,153건 |
| TP | 11,587건 |

### 저장
- `data/processed/day7_calibration_results.pkl`
- `data/processed/day7_results.pkl`

---

## Day 08 — SHAP / XAI

### 모델 구분
- **운영용 모델**: CalibratedClassifierCV 보정 모델 → `data/processed/day8_calibrated_lgbm.pkl`
- **해석용 모델**: 동일 하이퍼파라미터로 전체 데이터 재학습 (LightGBM), best_iteration=642 → `data/processed/day8_shap_model.pkl`

### 분석 방법
- SHAP TreeExplainer 사용
- 전역 해석 샘플: 20,000건 (사기 3,000건 + 정상 17,000건, seed=42)
- 타겟 인코딩: 전체 데이터 기준 (SHAP용, 시간적 누수 허용)

### SHAP 전역 중요도 상위 10위 (day8_shap_model 기준)

| 순위 | 변수 | 해석 |
|---|---|---|
| 1 | **card1** | 특정 카드 번호가 사기 패턴의 핵심 신호 (SHAP=1.492) |
| 2 | C13 | 값 낮을수록 사기 확률 증가 |
| 3 | C_PC1 | C컬럼군 PCA 주성분 |
| 4 | card2 | — |
| 5 | Transaction_day | 비선형 패턴 |
| 6 | P_emaildomain | — |
| 7 | C_PC2 | — |
| 8 | dist1 | — |
| 9 | addr1 | — |
| 10 | amt_robust_zscore | Day 3 파생변수 효과 검증 |

### 노트북 자체 메모
> "card1이 SHAP 중요도 1위로 나타난 것에 대해, 09_drift_analysis.ipynb에서 시간적 누수 여부와 스무딩 강도에 따른 과적합 여부를 추가로 검증했다."

### 저장
- `data/processed/day8_shap_values.pkl`
- `data/processed/day8_shap_model.pkl`
- `data/processed/day8_calibrated_lgbm.pkl`

---

## Day 09 — Drift 분석 및 방법론적 자기 검증

### 분할 설정 및 목적 구분

| 분할 | 기준 | 목적 |
|---|---|---|
| Day 04~08 GroupKFold | UID 기준 (시간 무관) | 모델 학습·평가용 |
| **Day 09 시계열 분할** | **month 0~4 vs 5+6** | **Drift 검증 전용 시뮬레이션** |

- 학습 구간(month 0~4): 495,904건 (사기 3.50%)
- 검증 구간(month 5+6): 94,636건 (사기 3.47%) — month 6은 2일치 8,111건이라 month 5와 병합

### 연속형 변수 PSI (153개 대상, Transaction_day 제외)

| 등급 | 기준 | 변수 수 |
|---|---|---|
| 안정 | PSI < 0.1 | 143개 |
| 주의 | 0.1 ≤ PSI < 0.2 | 4개 |
| Drift 위험 | PSI ≥ 0.2 | 6개 |

**PSI 상위 (Drift 위험):**

| 변수 | PSI |
|---|---|
| AllFlag_PC3 | 0.303304 |
| AllFlag_PC1 | 0.291121 |
| AllFlag_PC7 | 0.270904 |
| AllFlag_PC9 | 0.216702 |
| AllFlag_PC5 | 0.204033 |
| AllFlag_PC4 | 0.201911 |

- Transaction_day: PSI=6.901345 (구조적 단조 증가 → 분석에서 제외)

### KS Test (153개 대상)
- p < 0.05 (유의): 130개 / p ≥ 0.05 (안정): 23개
- KS 상위: AllFlag_PC3(0.186), AllFlag_PC1(0.180), D11(0.154)

### 범주형 변수 PSI (49개 대상)

| 등급 | 기준 | 변수 수 |
|---|---|---|
| 안정 | PSI < 0.1 | 38개 |
| 주의 | 0.1 ≤ PSI < 0.2 | 4개 |
| Drift 위험 | PSI ≥ 0.2 | 7개 |

**범주형 PSI 상위:**

| 변수 | PSI 원본 | 비고 |
|---|---|---|
| card1 | 2.426241 | → 재그룹핑 후 **0.002870** (구조적 착시) |
| id_31 | 0.831871 | → 재그룹핑 후 0.349798 (확정 Drift) |
| id_13 | 0.749038 | → 재그룹핑 후 0.557287 (확정 Drift) |
| M9 | 0.239618 | 저카디널리티, 확정 Drift |
| M8 | 0.239302 | 동상 |
| M7 | 0.239065 | 동상 |
| M2 | 0.200264 | 동상 |
| M3 | 0.198981 | 동상 |
| M1 | 0.198777 | 동상 |

### card1 PSI 구조적 착시 확인 (재그룹핑 검증)

`regroup_top_n(train, valid, top_n=20)` 적용 결과:
- card1: PSI **2.426 → 0.003**으로 사실상 소멸
- Other 비중: 학습 77.4% ↔ 검증 77.6% (거의 동일)
- 원인: 수천 개 희소 카테고리의 미세한 흔들림이 PSI 로그 항에서 증폭된 효과
- **결론: card1을 Drift 위험 리스트에서 완전 제외**

### 시간적 누수 발견 (핵심)

Day 8 모델이 전체 데이터로 타겟 인코딩 재계산했음을 실증 확인:

| card1 카테고리 | 학습 구간 평균 | 전체 데이터 평균 | 모델 인코딩값 |
|---|---|---|---|
| 7919 | 0.007709 | 0.007501 | **0.007537** |
| 9500 | 0.035647 | 0.037283 | **0.037280** |
| 15885 | 0.039480 | 0.042853 | **0.042838** |
| 17188 | 0.029650 | 0.026875 | **0.026891** |
| 15066 | 0.039394 | 0.039396 | **0.039385** |

→ 인코딩값이 `actual_mean_train_only`가 아닌 `actual_mean_full`과 일치 → **시간적 누수 확인**

### 보조 모델 재검증 (학습 구간 전용 재인코딩, m=10)

`target_encode_smoothed(train_raw, train_target, m=10)` 적용:

**Score PSI 비교:**

| 모델 | Score PSI | 학습 평균 예측확률 | 검증 평균 예측확률 |
|---|---|---|---|
| day8 최종모델 (누수 있음) | 0.0018 | 0.1416 | 0.1430 |
| **보조모델 (누수 제거)** | **0.0319** | **0.0350** | **0.0179** |

- Score PSI: 약 17배 상승, 여전히 "안정" 등급(< 0.1)
- **그러나** 검증 구간 평균 예측 사기확률이 학습 대비 약 **50% 하락** → PSI가 포착 못하는 잠재 성능 저하 신호

### SHAP 재계산 (보조모델 m=10, 20,000건 샘플)

| 변수 | SHAP (보조모델 m=10) | 순위 |
|---|---|---|
| card1 | 2.589198 | 1 |
| C13 | 1.888500 | 2 |
| C_PC1 | 1.360016 | 3 |
| card2 | 0.900344 | 4 |
| Transaction_day | 0.677267 | 5 |
| C_PC2 | 0.496961 | 6 |
| dist1 | 0.466623 | 7 |
| P_emaildomain | 0.445765 | 8 |
| addr1 | 0.442593 | 9 |
| V_group6_PC3 | 0.406039 | 10 |

### card1 스무딩 강도 비교 (과적합 진단)

**빈도 구간별 평균 |SHAP| 비교:**

| 빈도 구간 | m=10 | m=100 | 해석 |
|---|---|---|---|
| 1~5건 | 1.389 | 2.195 | — |
| 6~50건 | 2.434 | 2.032 | — |
| **51~500건** | **3.799** | **2.060** | **과적합 해소 확인** |
| 501~5,000건 | 2.403 | 2.328 | 거의 동일 |
| **5,000건 초과** | **1.556** | **1.550** | **진짜 신호 (안정)** |

**card1 SHAP 비교:**

| 모델 | SHAP | 순위 |
|---|---|---|
| day8 최종모델 (누수 있음) | 1.492 | 1위 |
| 보조모델 m=10 | 2.589 | 1위 |
| 보조모델 m=100 | 2.131 | 1위 |

- m=10에서 51~500건 구간 이상 급등(3.799) → m=100에서 2.060으로 해소 (과적합 확인)
- 5,000건 초과 구간은 스무딩 강도와 무관하게 일정 (1.556 → 1.550) → **진짜 신호 확인**
- **최종 판단**: card1의 SHAP 최상위권(1위)은 타당, 절대값은 저빈도 카테고리 과적합으로 다소 과대추정

### Drift 위험 변수와 SHAP 의존도 관계

| 변수 | PSI 등급 | SHAP 순위 (day8) | SHAP 순위 (보조모델 m=10) |
|---|---|---|---|
| card1 | 착시 → 제외 | 1위 | 1위 |
| AllFlag_PC3 | 우선 점검 | 38위 | 22위 |
| M3 | 확정 Drift | 31위 | 28위 |
| D11 | 국소 변화 | 33위 | 38위 |
| id_31 | 확정 Drift | 68위 | 70위 |
| M1 | 확정 Drift | 180위 | 178위 |

**→ 두 모델 모두 Drift 위험 변수 14개 중 SHAP 상위 20위 안에 든 변수가 없음 — 인코딩 방식과 무관하게 안정적으로 재현되는 결론**

### 종합 결론 5가지 (노트북 원문)

1. 입력 변수 수준에서는 결측 패턴(AllFlag_PC 계열), 검증 로직(M 계열), 기기 정보(id_13, id_31)에서 시간에 따른 실질적 분포 변화가 확인됨
2. 이 변수들은 모델의 예측 중요도(SHAP) 상위권과 겹치지 않아, 모델이 소수의 불안정한 변수에 과도하게 의존하지는 않는 것으로 판단됨
3. 다만 검증 구간에서 예측 사기확률이 체계적으로 낮아지는 경향이 확인되어, PSI만으로는 포착되지 않는 형태의 잠재적 성능 저하 신호가 존재함
4. day8 최종 모델(전체데이터 학습)은 배포용 아티팩트로서는 표준적이고 타당한 선택이나, 이를 이용한 시간적 일반화 검증(Drift 분석)에는 그대로 사용할 수 없으며, 별도의 학습구간 전용 재인코딩 모델이 필요함을 확인
5. card1과 같은 고카디널리티 식별자 변수는 타겟 인코딩 시 시간적 누수뿐 아니라 스무딩 강도에 따른 개별 샘플 과적합 여부도 별도로 점검해야 함

### 저장
- `data/processed/day9_drift_recheck_artifacts.pkl`

---

## 프로젝트 전체 핵심 수치 요약

| 항목 | 값 |
|---|---|
| 전체 샘플 수 | 590,540건 |
| 사기 비율 | 3.499% (20,663건) |
| 클래스 불균형 비율 | 1:27.6 |
| 데이터 기간 | 182일 (약 6.1개월) |
| 원본 컬럼 수 | 435개 (병합 + has_identity) |
| 최종 피처 수 | 203개 (모델 입력) |
| V컬럼 차원 감소 | 339개 → 89개 주성분 (72%) |
| VIF 개선 | 86,308 → 572 (99.3%) |
| LightGBM 기본 PR-AUC | 0.4860 |
| LightGBM 튜닝 후 PR-AUC | 0.5101 (+0.0241) |
| LightGBM 보정 후 PR-AUC | **0.5517** (+0.0416) |
| RF 보정 후 PR-AUC | 0.5100 |
| 최종 threshold | 0.20 |
| 최종 Precision / Recall / F1 | 0.4008 / 0.5608 / 0.4675 |
| Score PSI (day8, 누수 있음) | 0.0018 |
| Score PSI (보조모델, 누수 제거) | 0.0319 |
| card1 PSI 원본 | 2.426241 |
| card1 PSI 재그룹핑 후 | 0.002870 |
| card1 SHAP (day8) | 1.492 (1위) |
| card1 SHAP (보조모델 m=10) | 2.589 (1위) |
| card1 SHAP (보조모델 m=100) | 2.131 (1위) |
