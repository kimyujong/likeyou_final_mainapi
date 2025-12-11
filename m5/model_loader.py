import joblib
import numpy as np
import pandas as pd
from pathlib import Path
from tensorflow.keras.models import load_model
import tensorflow as tf
from sklearn.preprocessing import StandardScaler

# 모델 파일들이 위치한 기본 디렉토리 (환경변수나 설정으로 주입받을 수 있게 설계)
# 로컬 개발 시에는 절대 경로, 배포 시에는 상대 경로 등을 고려해야 함
# 여기서는 호출하는 쪽에서 base_path를 넘겨주도록 함

def regression_accuracy(y_true, y_pred):
    """모델 로드 시 필요한 커스텀 메트릭 함수"""
    tolerance = tf.constant(0.1, dtype=tf.float32)
    y_true = tf.cast(y_true, tf.float32)
    y_pred = tf.cast(y_pred, tf.float32)
    denom = tf.maximum(tf.abs(y_true), tf.constant(1.0, dtype=tf.float32))
    relative_error = tf.abs(y_true - y_pred) / denom
    return tf.reduce_mean(tf.cast(relative_error <= tolerance, tf.float32))

def restore_scaler_state(state):
    """저장된 딕셔너리 상태로부터 StandardScaler 객체 복원"""
    scaler = StandardScaler()
    scaler.mean_ = np.array(state['mean_'])
    scaler.scale_ = np.array(state['scale_'])
    scaler.var_ = np.array(state['var_'])
    scaler.n_features_in_ = state['n_features_in_']

    n_samples_seen = state.get('n_samples_seen_')
    if n_samples_seen is not None:
        scaler.n_samples_seen_ = np.array(n_samples_seen)
    else:
        scaler.n_samples_seen_ = None

    feature_names = state.get('feature_names_in_')
    if feature_names is not None:
        scaler.feature_names_in_ = np.array(feature_names, dtype=object)

    return scaler

def load_m5_model(model_dir: str, region_code: int):
    """
    특정 행정동 코드의 모델 번들(.pkl)과 모델(.keras)을 로드합니다.
    
    Args:
        model_dir (str): 모델 파일들이 있는 디렉토리 경로 (예: './saved_models')
        region_code (int): 행정동 코드 (예: 26500800)
        
    Returns:
        dict: 모델, 스케일러, 시드 데이터 등을 포함한 딕셔너리
    """
    base_path = Path(model_dir)
    bundle_path = base_path / f"final_model_{region_code}_bundle.pkl"
    
    if not bundle_path.exists():
        raise FileNotFoundError(f"모델 번들 파일을 찾을 수 없습니다: {bundle_path}")

    # 1. 메타데이터(Bundle) 로드
    metadata = joblib.load(bundle_path)

    # 2. .keras 모델 경로 찾기
    # 메타데이터에 저장된 경로는 학습 당시의 절대 경로일 수 있으므로, 
    # 파일명만 추출해서 현재 model_dir에서 찾습니다.
    original_model_path = Path(metadata["model_path"])
    model_filename = original_model_path.name
    current_model_path = base_path / model_filename
    
    if not current_model_path.exists():
        # 혹시 이름이 다를 수 있으니 metadata 경로 그대로도 한번 시도
        if original_model_path.exists():
            current_model_path = original_model_path
        else:
            raise FileNotFoundError(f"Keras 모델 파일을 찾을 수 없습니다: {current_model_path}")

    # 3. Keras 모델 로드
    model = load_model(
        str(current_model_path),
        custom_objects={
            "regression_accuracy": regression_accuracy,
            "acc": regression_accuracy
        }
    )

    # 4. 스케일러 복원
    feature_scaler = restore_scaler_state(metadata["feature_scaler"])
    target_scaler = restore_scaler_state(metadata["target_scaler"])

    # 5. 시드 데이터 복원
    seed_meta = metadata.get("seed_data")
    if not seed_meta:
        raise ValueError("모델 번들에 시드 데이터가 없습니다.")
        
    seed_df = pd.DataFrame(seed_meta["records"])
    if seed_meta.get("columns"):
        seed_df = seed_df[seed_meta["columns"]]
    seed_df = seed_df.reset_index(drop=True)

    return {
        "model": model,
        "feature_scaler": feature_scaler,
        "target_scaler": target_scaler,
        "feature_cols": metadata["feature_cols"],
        "seed_df": seed_df,
        "seq_len": metadata.get("seq_len", len(seed_df))
    }

