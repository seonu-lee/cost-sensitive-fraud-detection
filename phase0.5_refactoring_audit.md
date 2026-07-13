# Phase 0.5 — 리팩토링 사전 점검 보고서
**작성일**: 2026-07-13  
**점검 범위**: notebooks/01~09, src/, data/processed/ 산출물 전수 점검

---

## 점검 항목 요약표

| Day | 점검항목 | 판정 | 상세 내용 | 권장 조치 |
|---|---|---|---|---|
| Day 01 | 노트북 간 수동 의존성 | 문제없음 | raw CSV → `day1_merged.parquet` 저장. 경로는 상대경로(`../data/raw`) | — |
| Day 01 | 전처리기 저장 | 문제없음 | 이 단계에서는 `reduce_mem_usage` 함수만 사용, fit 상태 보존 필요 없음 | — |
| Day 01 | 하드코딩 경로 | 문제없음 | `DATA_DIR = "../data/raw"` 상대경로 | — |
| Day 01 | 연산 비용 | 문제없음 | CSV 로딩 + downcasting, 수 분 내 완료 | — |
| Day 01 | MLflow 로깅 | 신규 작성 필요 | 없음 | mlflow.log_param/metric 추가 |
| Day 01 | 아티팩트 완결성 | 문제없음 | `day1_merged.parquet`(590540×437) 저장, dtype 보존 확인됨 | — |
| Day 02 | 노트북 간 수동 의존성 | 문제없음 | `day1_merged.parquet` 불러오기. 통계검정 결과는 사람이 읽는 용도, 분기 자동화 가능 | — |
| Day 02 | 전처리기 저장 | 문제없음 | 이 단계에서는 스케일러/인코더 없음. V그룹 결측 플래그는 코드로 재현 가능 | — |
| Day 02 | 하드코딩 경로 | 문제없음 | 상대경로만 사용 | — |
| Day 02 | 연산 비용 | 문제없음 | 통계검정(chi2, Mann-Whitney) + Bootstrap CI(1000회), 10분 이내 | — |
| Day 02 | MLflow 로깅 | 신규 작성 필요 | 없음 | 검정 결과 테이블 log_artifact 추가 |
| Day 02 | 아티팩트 완결성 | 문제없음 | `day2_merged.parquet` 저장 | — |
| Day 03 | 노트북 간 수동 의존성 | **보완 필요** | 셀 내 V그룹 PCA 목표 분산 비율(`pca_config`) 수동 설정값이 하드코딩. PCA 적용 여부 결정(V_group13·14 제외)도 하드코딩 상수로 고정됨 | `pca_config` 딕셔너리를 config 파일로 분리 |
| Day 03 | 전처리기 저장 | **보완 필요 (최우선)** | V그룹 PCA 모델 13개, C컬럼 PCA/Scaler, AllFlag PCA/Scaler, MissingFlag PCA/Scaler — 모두 `day3_artifacts.pkl`에 저장되어 있지 않음. pkl은 `v_groups`(DataFrame), `categorical_cols`(list), `final_columns`(list)만 보유 | 모든 PCA·Scaler 객체를 `day3_artifacts.pkl`에 추가 저장 |
| Day 03 | 하드코딩 경로 | 문제없음 | `../data/processed/`, `../reports/figures/` 상대경로 | — |
| Day 03 | 연산 비용 | **보완 필요** | VIF 계산(339개 컬럼 × 591k 행), 다중공선성 해소 PCA 반복 등 총 30분+ 예상. 자동화 파이프라인에서 매 실행 시 재계산은 비효율적 | PCA는 저장된 모델로 transform만 실행 |
| Day 03 | MLflow 로깅 | 신규 작성 필요 | 없음 | PCA 설명분산 비율, 최종 컬럼 수 log_metric 추가 |
| Day 03 | 아티팩트 완결성 | **보완 필요 (최우선)** | PCA 모델/스케일러 미저장. `day3_artifacts.pkl`에는 컬럼 목록만 있고 변환 객체 없음 → 새 데이터 변환 불가 | V그룹별 PCA+Scaler, C/AllFlag/MissingFlag PCA+Scaler 저장 필수 |
| Day 04 | 노트북 간 수동 의존성 | **보완 필요** | **GroupKFold → StratifiedGroupKFold 교체**: fold 2의 사기 비율 불균형을 확인 후 코드를 직접 수정하여 고정됨. 최종 코드에는 `sgkf = StratifiedGroupKFold(n_splits=5)`로 하드코딩 완료. 자동화 시 StratifiedGroupKFold로 고정하면 됨 | 파이프라인에서 StratifiedGroupKFold로 명시 고정 |
| Day 04 | 전처리기 저장 | **보완 필요 (최우선)** | CV 루프 내 `scaler = StandardScaler()` 및 `target_encode(smoothing=20)` 맵이 fold마다 새로 계산되고 **저장되지 않음**. 최종 배포용 scaler·인코딩 맵 없음 | 전체 데이터 기준 scaler·인코딩 맵 별도 저장 필요 |
| Day 04 | 하드코딩 경로 | 문제없음 | 상대경로 | — |
| Day 04 | 연산 비용 | **보완 필요** | 4개 모델 × 5-fold CV, RF 기준 fold당 약 5분, 총 약 20~30분. 재자동화 시 매번 4개 모델 재학습은 불필요 | 최종 LightGBM 단일 모델만 재학습하도록 파이프라인 설계 |
| Day 04 | MLflow 로깅 | 신규 작성 필요 | 없음 | fold별 PR-AUC/ROC-AUC, OOF 최종 성능 log_metric 추가 |
| Day 04 | 아티팩트 완결성 | **보완 필요** | `day4_oof_results.pkl`에 OOF 예측값만 있고 **모델 객체 없음**. fold 인덱스 미저장. random_state=42는 코드에 하드코딩됨 | 최소한 최종 선택 모델(LightGBM) 객체 저장 필요 |
| Day 05 | 노트북 간 수동 의존성 | 문제없음 | `day4_oof_results.pkl`만 불러와 통계검정. 모델 재학습 없음 | — |
| Day 05 | 전처리기 저장 | 문제없음 | 전처리 없음 (OOF 예측값으로만 검정) | — |
| Day 05 | 하드코딩 경로 | 문제없음 | 상대경로 | — |
| Day 05 | 연산 비용 | 문제없음 | Bootstrap CI 1000회, 수 분 내 완료 | — |
| Day 05 | MLflow 로깅 | 신규 작성 필요 | 없음 | DeLong/Bootstrap CI 결과 log_metric 추가 |
| Day 05 | 아티팩트 완결성 | 문제없음 | `day5_results.pkl`에 검정 결과 DataFrame 저장 | — |
| Day 06 | 노트북 간 수동 의존성 | **보완 필요** | Optuna 튜닝 결과(best params)가 저장되어 있고 자동으로 불러올 수 있으나, RF/XGBoost 튜닝 보류 결정은 "trial당 25분+"이라는 수동 관찰에 기반 → 자동화 시 LightGBM만 재튜닝하도록 명시 | LightGBM 단독 튜닝 파이프라인으로 고정 |
| Day 06 | 전처리기 저장 | **보완 필요** | CV 루프 내 scaler/인코더 매번 재계산, 저장 없음 (Day 04와 동일 패턴) | Day 04 개선과 연계 처리 |
| Day 06 | 하드코딩 경로 | 문제없음 | 상대경로 | — |
| Day 06 | 연산 비용 | **보완 필요 (주의)** | Optuna 20 trials × 5-fold = 총 **62분** 소요. 자동 재학습 시 매번 재튜닝은 비현실적 | 하이퍼파라미터 고정 후 학습만 반복. 재튜닝은 별도 스케줄로 분리 |
| Day 06 | MLflow 로깅 | 신규 작성 필요 | 없음 | Optuna best params, best PR-AUC log_param/metric 추가 |
| Day 06 | 아티팩트 완결성 | **보완 필요** | `day6_tuning_results.pkl`에 Optuna study 객체 + best params 저장. 그러나 학습된 모델 객체는 없음 | best params는 저장됨. 이를 사용해 Day 08에서 재학습 → 현재 구조는 OK |
| Day 07 | 노트북 간 수동 의존성 | **보완 필요** | `day6_tuning_results.pkl`에서 best params 자동 로드 가능. threshold=0.20 선정(FN:FP=7.5:1)은 `day7_results.pkl`에 하드코딩되어 있어 재활용 가능 | threshold 값을 config에서 읽도록 변경 |
| Day 07 | 전처리기 저장 | **보완 필요** | CV 루프 내 scaler/인코더 매번 재계산, 저장 없음 | Day 04와 연계 처리 |
| Day 07 | 하드코딩 경로 | 문제없음 | 상대경로 | — |
| Day 07 | 연산 비용 | **보완 필요** | CalibratedClassifierCV(cv=5) × 2모델 × StratifiedGroupKFold 5-fold = 상당한 연산. LightGBM 단독이면 약 30~40분 예상 | 최종 모델(LightGBM)만 보정, RF는 제외 |
| Day 07 | MLflow 로깅 | 신규 작성 필요 | 없음 | 보정 전후 PR-AUC, Calibration Gap, threshold log_metric 추가 |
| Day 07 | 아티팩트 완결성 | **보완 필요** | **Day 07에서 모델 객체 저장 누락** — Day 08 주석에 "Day 7에서 모델 객체 저장이 누락되어 재학습이 필요합니다"라고 명시됨. `day7_calibration_results.pkl`은 OOF preds/metrics만 보유 | Day 07에서 calibrated model 저장 추가 (또는 Day 07 종료 시점을 최종 모델 저장 시점으로 명시) |
| Day 08 | 노트북 간 수동 의존성 | **보완 필요** | SHAP TreeExplainer(전체 예측 기여값 계산)는 별도 해석 단계이나, 학습 코드가 Day 08에 포함되어 있어 파이프라인 경계가 불명확 | 운영 모델 저장(Day 07 종료)과 SHAP 분석을 별도 단계로 분리 |
| Day 08 | 전처리기 저장 | **부분 해결** | `day8_calibrated_lgbm.pkl`에 `scaler`(StandardScaler, 전체 데이터 fit) 저장됨. 단, 타겟 인코딩 맵은 `X_full`에 이미 적용된 상태로만 존재 — 새 데이터에 맵을 개별 적용하려면 맵 자체가 필요하나 없음 | 타겟 인코딩 맵(49개 컬럼별 {범주: 인코딩값} dict) 별도 저장 필요 |
| Day 08 | 하드코딩 경로 | 문제없음 | 상대경로 | — |
| Day 08 | 연산 비용 | **보완 필요 (주의)** | **SHAP TreeExplainer**: `shap.TreeExplainer(shap_model).shap_values(X_shap_global)` 호출 — `pred_contrib`으로 대체되지 않고 원본 SHAP 계산 사용. 20,000건 샘플 기준. 시간 측정값은 코드에 없으나 유사 환경에서 수십~90분 소요 가능 | SHAP 분석은 정기 재학습 파이프라인과 분리, 별도 스케줄 실행 |
| Day 08 | MLflow 로깅 | 신규 작성 필요 | 없음 | 최종 모델 log_model, SHAP 이미지 log_artifact 추가 |
| Day 08 | 아티팩트 완결성 | **부분 해결** | `day8_calibrated_lgbm.pkl`: model + scaler 저장 ✅. `day8_shap_model.pkl`: 해석용 모델 저장 ✅. `day8_shap_values.pkl`: SHAP 값 저장 ✅. **단, 타겟 인코딩 맵 미저장** — `X_full` DataFrame에 이미 적용된 값만 있음 | 인코딩 맵 별도 저장 |
| Day 09 | 노트북 간 수동 의존성 | **보완 필요** | **card1 재그룹핑** (`regroup_top_n`, top_n=20): Day 09 분석 전용, 운영 모델(day8_calibrated_lgbm)에는 적용 안 됨. **스무딩 m=10/m=100**: Day 09 재검증에서 m=10(recheck), m=100(추가 검증) 사용 — 운영 모델은 smoothing=20 유지. 두 결정 모두 분석 노트북 내 코드로 고정되어 있으며 운영 경로에는 영향 없음 | Day 09 결론("card1 SHAP 1위는 robust, 절대값은 다소 과대추정")을 config/README에 문서화 |
| Day 09 | 전처리기 저장 | 문제없음 (재검증용만) | `day9_drift_recheck_artifacts.pkl`에 `encoding_maps`(49컬럼), `scaler_re`(StandardScaler) 저장됨. 단, 이는 재검증 보조 모델용이며 운영 경로의 객체가 아님 | — |
| Day 09 | 하드코딩 경로 | 문제없음 | 상대경로 | — |
| Day 09 | 연산 비용 | **보완 필요** | PSI 계산, 타임슬라이싱 후 재학습, SHAP 재계산 — 총 수십 분 소요. Drift 분석은 주기적 모니터링 태스크로 파이프라인 분리 필요 | Drift 모니터링 전용 DAG 분리 |
| Day 09 | MLflow 로깅 | 신규 작성 필요 | 없음 | PSI 값, Score PSI log_metric 추가 |
| Day 09 | 아티팩트 완결성 | 문제없음 (재검증 범위) | `day9_drift_recheck_artifacts.pkl`에 재검증 모델 + 인코딩 맵 + SHAP값 저장. Drift 분석 결론은 노트북 내 텍스트로만 존재 | Drift 판정 기준(PSI > 0.2 등)을 config로 분리 |

---

## 6가지 항목별 전체 요약

### 1. 노트북 간 수동 의존성

**Day 04 — GroupKFold → StratifiedGroupKFold 교체 확인**
- 최종 코드 위치: 셀 `acf7ce56` 내 `run_cv` 함수
- 코드: `sgkf = StratifiedGroupKFold(n_splits=5)` — **하드코딩 완료**
- 교체 근거(사람의 판단 시점): fold 2 사기 비율 2.87% 확인 후 코드 수정
- 자동화 영향: 파이프라인에서 StratifiedGroupKFold를 명시적으로 지정하면 됨 ✅

**Day 09 — card1 재그룹핑 및 스무딩 강도 결정 확인**
- card1 재그룹핑(`top_n=20`): 코드 위치 Day 09 셀 라인 877. **분석 전용** — 운영 모델에 적용 안 됨
- 스무딩 m=10: Day 09 재검증 보조 모델에서만 사용(`target_encode_smoothed(..., m=10)`)
- 스무딩 m=100: Day 09에서 card1 한정 추가 검증용 — 운영 모델에 적용 안 됨
- **운영 모델(day8_calibrated_lgbm)의 타겟 인코딩**: 전체 데이터 기준, smoothing=20(Day 04 `target_encode` 함수 기본값) 적용
- 결론: m=10 vs m=100 판단은 **코드에서 "실험적으로 확인"한 것이며 최종 운영 경로 변경으로 이어지지 않았음**. 보고서 문서화 필요

### 2. 전처리기(스케일러/인코더/PCA) 객체 저장 현황

| 객체 | Day | 저장 여부 | 저장 경로 | 비고 |
|---|---|---|---|---|
| V그룹 PCA × 13개 | 03 | ❌ 미저장 | — | 노트북 재실행 없이 새 데이터 변환 불가 |
| V그룹 Scaler × 13개 | 03 | ❌ 미저장 | — | 동일 |
| C컬럼 PCA (`pca_c`) | 03 | ❌ 미저장 | — | C_PC1, C_PC2 생성에 사용 |
| C컬럼 Scaler (`scaler_c`) | 03 | ❌ 미저장 | — | 동일 |
| AllFlag PCA | 03 | ❌ 미저장 | — | AllFlag_PC1~9 생성에 사용 |
| AllFlag Scaler | 03 | ❌ 미저장 | — | 동일 |
| MissingFlag PCA | 03 | ❌ 미저장 | — | V그룹 결측 플래그 통합 |
| 타겟 인코딩 맵 (fold내) | 04 | ❌ 미저장 | — | fold마다 재계산 |
| StandardScaler (fold내) | 04/06/07 | ❌ 미저장 | — | fold마다 재계산 |
| StandardScaler (전체 fit) | 08 | ✅ 저장됨 | `day8_calibrated_lgbm.pkl['scaler']` | 추론용 |
| 타겟 인코딩 맵 (전체 fit) | 08 | ❌ 미저장 | `X_full`에 적용된 값만 있음 | 새 데이터 인코딩 불가 |
| 타겟 인코딩 맵 (재검증) | 09 | ✅ 저장됨 | `day9_drift_recheck_artifacts.pkl['encoding_maps']` | 재검증 모델 전용 |

### 3. 하드코딩된 경로

**모든 노트북에서 Windows 절대경로(`C:\Users\`) 미사용** — 코드 내 경로는 전부 상대경로.  
(에러 메시지 출력에서 `C:\Users\seonu\AppData\...` 형태가 나타나지만 이는 stderr 출력이며 코드 경로가 아님)

| 경로 패턴 | 사용 위치 | 현황 | 권장 조치 |
|---|---|---|---|
| `"../data/raw"` | Day 01 | 상대경로 ✅ | 환경변수 `DATA_DIR`로 대체 권장 |
| `"../data/processed/"` | 모든 Day | 상대경로 ✅ | `PROCESSED_DIR` 환경변수로 대체 |
| `"../reports/figures/"` | Day 01, 02, 04, 05, 08 | 상대경로 ✅ | `REPORTS_DIR` 환경변수로 대체 |

Airflow DAG에서는 절대경로 또는 Airflow Variable/환경변수를 사용해야 하므로, 상대경로 전체를 환경변수 기반으로 교체하는 리팩토링이 필요함.

### 4. 연산 비용이 큰 작업

| Day | 작업 | 실측/예상 시간 | 자동화 시 처리 방식 |
|---|---|---|---|
| Day 06 | LightGBM Optuna 20 trials | **62분** (실측) | best_params 고정 후 재튜닝 생략. 별도 튜닝 DAG로 분리 |
| Day 06 | RF trial당 OOB 탐색 | ~25분+/trial | RF 제외 확정 (LightGBM만 운영) |
| Day 07 | CalibratedClassifierCV × LightGBM | 약 30~40분 예상 | 단독 보정 스텝으로 분리 가능 |
| Day 08 | SHAP TreeExplainer (20,000건) | 수십~90분 예상 | 재학습 파이프라인과 분리. 주1회 별도 실행 |
| Day 03 | VIF 계산 + 다중공선성 PCA | 30분+ 예상 | 저장된 PCA 객체 재사용으로 해결 |

**Day 08 SHAP 주의**: `pred_contrib`으로 대체되지 않았음. `explainer.shap_values(X_shap_global)` 전체 SHAP 계산 사용. 운영 파이프라인에서 SHAP 분석이 병목이 될 수 있으므로 **별도 비정기 DAG**로 분리 권장.

### 5. MLflow 로깅 코드 존재 여부

**전체 9개 노트북 모두 MLflow 로깅 없음** — 신규 작성 필요.  
(reports/final_report/generate_report_part2.py에서 MLflow가 "2단계 계획"으로 언급되나 실제 코드 없음)

각 Day별 로깅 대상:

| Day | log_param 대상 | log_metric 대상 | log_artifact 대상 |
|---|---|---|---|
| 01 | — | — | day1_merged.parquet |
| 02 | — | cramers_v, effect_size_r | day2_merged.parquet |
| 03 | pca_config (분산 비율) | 압축 전후 컬럼 수 | day3_artifacts.pkl, day3_final.parquet |
| 04 | n_splits, smoothing, scale_pos_weight | fold별/평균 PR-AUC, ROC-AUC | day4_oof_results.pkl |
| 05 | n_bootstrap | delong_p, bootstrap_ci 상하한 | day5_results.pkl |
| 06 | LightGBM best_params | best_pr_auc | day6_tuning_results.pkl |
| 07 | final_threshold, fn_cost, fp_cost | pr_auc_calibrated, calibration_gap | day7_results.pkl |
| 08 | — | — | day8_calibrated_lgbm.pkl, day8_shap_bar.png |
| 09 | psi_threshold | score_psi, feature_psi 상위 | day9_drift_recheck_artifacts.pkl |

### 6. 모델/아티팩트 저장 완결성

| 파일 | 저장된 것 | 누락된 것 |
|---|---|---|
| `day3_artifacts.pkl` | v_groups(DataFrame), categorical_cols, final_columns | **V그룹 PCA×13, C PCA, AllFlag PCA, MissingFlag PCA, 각 Scaler** |
| `day4_oof_results.pkl` | oof_preds, oof_labels, 성능 지표 (4모델) | **모델 객체**, fold 인덱스 |
| `day5_results.pkl` | 검정 결과 DataFrame 4종 | — |
| `day6_tuning_results.pkl` | Optuna study, best_params, 성능 비교 | 학습된 모델 객체(필요 없음, Day08서 재학습) |
| `day7_calibration_results.pkl` | OOF preds, 성능 지표 (2모델) | **보정된 모델 객체** (Day08 주석에서 누락 명시) |
| `day7_results.pkl` | final_model명, final_threshold, 시나리오 DataFrame | 모델 객체 |
| `day8_calibrated_lgbm.pkl` | model(CalibratedClassifierCV), scaler, X_full | **타겟 인코딩 맵** |
| `day8_shap_model.pkl` | LGBMClassifier (해석용) | — |
| `day8_shap_values.pkl` | shap_values, X_shap_global, feature_names | — |
| `day9_drift_recheck_artifacts.pkl` | encoding_maps, scaler_re, model_re, SHAP 결과 | — (재검증 목적 충족) |

---

## 리팩토링 우선순위

### 최우선 (파이프라인 이식 자체가 불가능한 블로커)

**1. Day 03 — PCA/Scaler 객체 저장 (블로커 #1)**
- 현재 `day3_artifacts.pkl`에는 컬럼 목록만 있고 변환 객체가 없음
- 새 데이터를 `day3_final.parquet`과 동일한 형태로 변환하려면 V그룹 PCA×13 + C PCA + AllFlag PCA + MissingFlag PCA + 각 Scaler가 모두 필요함
- 노트북 03에 저장 코드 추가 후 `day3_artifacts.pkl` 재생성이 최우선

**2. Day 08 — 타겟 인코딩 맵 저장 (블로커 #2)**
- `day8_calibrated_lgbm.pkl`에 scaler는 있으나 타겟 인코딩 맵(49개 컬럼 × {범주: 인코딩값}) 없음
- 새 거래 1건이 들어왔을 때 card1, ProductCD 등을 인코딩할 방법이 없음
- 맵을 pkl에 추가하거나 Day 09 `encoding_maps`를 production 경로에 정식 연결

### 1순위 (자동화 DAG 설계에 직결되는 사항)

**3. 경로를 환경변수로 교체 — 모든 노트북**
- `"../data/raw"`, `"../data/processed/"` 등 상대경로를 `os.environ['DATA_DIR']` 등으로 교체
- Airflow DAG에서는 절대경로 또는 Variable이 필요

**4. 전처리 파이프라인을 단일 재사용 함수로 통합 — Day 03~08 공통**
- 현재 `target_encode`, `StandardScaler` fit이 Day 04, 06, 07, 08에서 각각 별도 정의/재실행됨
- `src/feature_engineering.py`에 통합하여 단일 진입점으로 만들기

**5. 연산 비용 큰 스텝 분리**
- Optuna 튜닝(62분): 별도 튜닝 DAG로 분리, 정기 재학습 DAG는 best_params로 학습만
- SHAP 분석(수십~90분): 별도 분석 DAG로 분리, 주1회 또는 모델 변경 시에만 실행

### 2순위 (안정성·재현성 향상)

**6. Day 04 — fold 인덱스 저장**
- 통계검정·재현을 위해 fold 인덱스(각 fold의 val_idx)를 pkl에 함께 저장

**7. Day 07 — 보정 모델 저장 시점 Day 07로 이동**
- 현재 Day 07 종료 시점에 모델 미저장 → Day 08에서 재학습
- Day 07 파이프라인 종료 시 즉시 저장하도록 변경

**8. MLflow 로깅 추가 — 모든 Day**
- 각 스텝별 log_param/log_metric/log_artifact 추가
- 실험 트래킹 없이는 자동화 파이프라인 운영 불가

### 3순위 (이식 완성 후 개선)

**9. Day 09 — Drift 판정 config화**
- PSI > 0.2 등 임계값을 코드 상수에서 config 파일로 분리

**10. src/ 확장**
- 현재 `src/`에는 `data_utils.py`, `eval_metrics.py`, `feature_engineering.py`, `cv_utils.py`, `viz_utils.py`가 있으나 실제 노트북에서 활용이 적음
- 전처리 파이프라인, PCA 변환, 타겟 인코딩을 `src/`로 이식하여 노트북을 호출 레이어로만 활용

---

## 리팩토링 권장 순서 (Day 기준)

```
Day 03 PCA 저장 추가
    → Day 08 인코딩 맵 저장 추가
        → 경로 환경변수 교체 (전체)
            → src/ 전처리 함수 통합
                → MLflow 로깅 추가 (Day별 순차)
                    → Optuna/SHAP DAG 분리
                        → Day 07 모델 저장 시점 정정
```

**핵심 원칙**: Day 03과 Day 08 수정 없이는 어떤 새 데이터도 운영 모델에 통과시킬 수 없다. 이 두 스텝이 전체 파이프라인의 병목.
