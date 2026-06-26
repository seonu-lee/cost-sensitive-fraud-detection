"""
비용 민감형 사기탐지 프로젝트 - 통계검정 및 평가 지표 함수 모듈

Day 2(통계검정)에서 정의한 함수들을 모듈화하여 노트북마다 재정의하지 않고
`from src.eval_metrics import ...` 형태로 불러와 사용한다.
"""

import numpy as np
import pandas as pd
from scipy import stats
from scipy.stats import mannwhitneyu


def chi_square_test(df, col, target='isFraud'):
    """
    범주형 변수와 타겟 간 카이제곱 독립성 검정을 수행한다.

    표본이 큰 경우 p-value만으로는 실질적 연관 강도를 판단하기 어려우므로,
    Cramér's V(0~1)를 함께 산출하여 효과크기를 같이 확인한다.

    Parameters
    ----------
    df : pd.DataFrame
        분석 대상 데이터프레임
    col : str
        검정할 범주형 변수 컬럼명
    target : str, default 'isFraud'
        타겟 변수 컬럼명

    Returns
    -------
    dict : variable, chi2, p_value, dof, cramers_v, significant
    """
    contingency = pd.crosstab(df[col], df[target])
    chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

    n = contingency.sum().sum()
    min_dim = min(contingency.shape) - 1
    cramers_v = np.sqrt(chi2 / (n * min_dim)) if min_dim > 0 else np.nan

    return {
        'variable': col,
        'chi2': chi2,
        'p_value': p_value,
        'dof': dof,
        'cramers_v': cramers_v,
        'significant': p_value < 0.05
    }


def mannwhitney_test(df, col, target='isFraud'):
    """
    연속형 변수와 타겟(이진) 간 Mann-Whitney U test를 수행한다.

    정규성이 충족되지 않는 변수(왜도/첨도가 큰 경우)에 대해 t-test 대신
    사용하는 비모수 검정이며, 효과크기는 rank-biserial correlation으로 산출한다.

    Parameters
    ----------
    df : pd.DataFrame
        분석 대상 데이터프레임
    col : str
        검정할 연속형 변수 컬럼명
    target : str, default 'isFraud'
        타겟 변수 컬럼명 (이진, 0/1)

    Returns
    -------
    dict : variable, median_normal, median_fraud, u_stat, p_value, effect_size_r, significant
    """
    group0 = df.loc[df[target] == 0, col].dropna()
    group1 = df.loc[df[target] == 1, col].dropna()

    u_stat, p_value = mannwhitneyu(group0, group1, alternative='two-sided')

    n0, n1 = len(group0), len(group1)
    r_effect = 1 - (2 * u_stat) / (n0 * n1)

    return {
        'variable': col,
        'median_normal': group0.median(),
        'median_fraud': group1.median(),
        'u_stat': u_stat,
        'p_value': p_value,
        'effect_size_r': abs(r_effect),
        'significant': p_value < 0.05
    }


def reduce_mem_usage(df, verbose=True):
    """
    컬럼별 값 범위를 확인해 더 작은 dtype으로 다운캐스팅한다 (Day 1에서 정의).

    정수형은 값 범위 내 무손실 변환이며, 실수형은 float32 변환 시 미세한
    정밀도 손실이 발생할 수 있으나(Day 1 검증: 최대 오차 8.79e-05) 분석에는
    영향이 없는 수준임을 확인하였다.

    Parameters
    ----------
    df : pd.DataFrame
    verbose : bool, default True
        변환 전후 메모리 사용량을 출력할지 여부

    Returns
    -------
    pd.DataFrame : 다운캐스팅된 데이터프레임
    """
    start_mem = df.memory_usage(deep=True).sum() / 1024**2

    for col in df.columns:
        col_type = df[col].dtype

        if col_type != object:
            c_min = df[col].min()
            c_max = df[col].max()

            if str(col_type)[:3] == 'int':
                if c_min > np.iinfo(np.int8).min and c_max < np.iinfo(np.int8).max:
                    df[col] = df[col].astype(np.int8)
                elif c_min > np.iinfo(np.int16).min and c_max < np.iinfo(np.int16).max:
                    df[col] = df[col].astype(np.int16)
                elif c_min > np.iinfo(np.int32).min and c_max < np.iinfo(np.int32).max:
                    df[col] = df[col].astype(np.int32)
                else:
                    df[col] = df[col].astype(np.int64)
            else:
                if c_min > np.finfo(np.float32).min and c_max < np.finfo(np.float32).max:
                    df[col] = df[col].astype(np.float32)
                else:
                    df[col] = df[col].astype(np.float64)
        else:
            df[col] = df[col].astype('category')

    end_mem = df.memory_usage(deep=True).sum() / 1024**2
    if verbose:
        print(f"메모리 사용량: {start_mem:.2f} MB → {end_mem:.2f} MB "
              f"({100*(start_mem-end_mem)/start_mem:.1f}% 감소)")

    return df