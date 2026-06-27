"""
중간 산출물(DataFrame이 아닌 보조 정보) 저장/복원 유틸리티.
v_groups, PCA 모델 객체, 변수 목록 등 parquet에 담기지 않는 정보를 보존한다.
"""

import pickle
import json
import os


def save_artifacts(artifacts: dict, path: str):
    """딕셔너리 형태의 중간 산출물을 pickle로 저장한다.
    
    Parameters
    ----------
    artifacts : dict
        예: {'v_groups': v_groups, 'pca_models': {...}, 'categorical_cols': [...]}
    path : str
        저장 경로 (.pkl)
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        pickle.dump(artifacts, f)
    print(f"중간 산출물 저장 완료: {path}")


def load_artifacts(path: str) -> dict:
    """저장된 중간 산출물을 복원한다."""
    with open(path, 'rb') as f:
        artifacts = pickle.load(f)
    print(f"중간 산출물 복원 완료: {path} (키: {list(artifacts.keys())})")
    return artifacts