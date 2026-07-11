# 비용 민감형 금융 사기탐지 모델 개발 및 통계적 성능 검증

IEEE-CIS Fraud Detection 데이터셋을 활용해, 사기탐지 모델을 개발하고 그 성능·안정성을 통계적으로 검증한 프로젝트입니다. 단순 모델 성능 비교에 그치지 않고, **모델 선택의 통계적 근거 마련 → 하이퍼파라미터 튜닝 → 설명가능성 분석 → 운영 관점의 Drift(분포 변화) 검증**까지 실무형 파이프라인 전 과정을 다룹니다.

## 데이터셋

- [IEEE-CIS Fraud Detection](https://www.kaggle.com/competitions/ieee-fraud-detection) (Kaggle)
- Transaction 590,540건 + Identity 144,233건, 사기 비율 약 3.5%
- `data/raw/`에 위치시켜야 하며, 용량 문제로 레포에는 포함하지 않음 (`.gitignore` 처리)

## 프로젝트 구조

```
cost-sensitive-fraud-detection/
├── notebooks/
│   ├── 01_data_loading_eda.ipynb          # 데이터 로딩, 결측률, 기초통계
│   ├── 02_statistical_tests.ipynb         # 카이제곱/t-test, 클래스 불균형 분석
│   ├── 03_feature_engineering.ipynb       # UID, 집계변수, 결측플래그, 시간파생변수
│   ├── 04_cv_strategy_model_compare.ipynb # GroupKFold, 4개 모델 비교 (PR-AUC/ROC-AUC)
│   ├── 05_statistical_validation.ipynb    # McNemar, DeLong, Bootstrap CI
│   ├── 06_hyperparameter_tuning.ipynb     # Optuna 기반 튜닝
│   ├── 07_calibration_threshold.ipynb     # Calibration, 비용 민감형 Threshold 최적화
│   ├── 08_shap_xai.ipynb            # SHAP 기반 모델 해석
│   └── 09_drift_analysis.ipynb            # PSI/KS Test 기반 시간적 분포 안정성 검증
├── src/                                    # 재사용 함수 모듈 (data_utils, cv_utils, eval_metrics 등)
├── data/                                   # raw/processed 데이터 (.gitignore)
├── models/                                 # 학습된 모델 아티팩트 (.gitignore)
└── reports/                                # 최종 보고서, 시각화 산출물
```

## 분석 파이프라인

```
데이터 이해(01~03) → 모델 비교(04) → 통계적 검증(05) → 튜닝(06)
→ Calibration/Threshold(07) → 설명가능성(08) → Drift 분석(09)
```

## 핵심 방법론

| 단계 | 방법론 |
|---|---|
| 검증 전략 | GroupKFold (UID 기준, 동일 사용자 거래의 train/valid 분리 방지) |
| 평가지표 | PR-AUC(핵심), ROC-AUC(보조) — 클래스 불균형(3.5%) 고려 |
| 모델 선택 | McNemar/DeLong Test로 통계적 유의성 검증 후 실용성 기준 최종 선택 |
| 튜닝 | Optuna 기반 베이지안 최적화 |
| 설명가능성 | SHAP (TreeSHAP, LightGBM `pred_contrib` 활용) |
| Drift 검증 | PSI + KS Test (연속형), 범주형 PSI + 카이제곱 (범주형), 모델 예측확률 PSI |

## 주요 발견 사항

- **통계적 동점 모델의 실용적 선택**: Random Forest와 LightGBM의 PR-AUC 차이는 통계적으로 유의하지 않음을 확인 → 배포 용이성 등 실용적 이유로 LightGBM 최종 선택
- **고카디널리티 변수의 지표 왜곡 검증**: card1(카드 식별 변수)의 PSI가 2.43으로 비정상적으로 높게 나왔으나, 재그룹핑 검증을 통해 희소 카테고리로 인한 구조적 착시임을 실증
- **데이터 누수 자기 발견 및 보정**: 배포용 최종 모델(전체 데이터 학습)을 시간 기반 Drift 검증에 그대로 사용하면 안 된다는 점을 실증적으로 발견, 학습 구간 전용 재인코딩 보조 모델로 재검증
- **단일 지표의 한계 인지**: Score PSI가 "안정"으로 나와도 예측 확률 평균이 학습 대비 검증 구간에서 약 50% 낮아지는 현상을 별도로 확인 — PSI만으로 운영 리스크를 판단하는 것의 한계를 짚음

## 기술 스택

Python, Pandas, NumPy, Scikit-learn, LightGBM, XGBoost, Optuna, SHAP, SciPy/Statsmodels, Matplotlib

## 자세한 분석 서사

Day 01~09 전체 분석 과정과 의사결정 근거는 [`프로젝트_전체_서사_정리.md`](./프로젝트_전체_서사_정리.md)에 정리되어 있습니다.
