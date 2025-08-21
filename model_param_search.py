# hyperparameter_tuning.py (로컬에서 실행)
import joblib
from sklearn.calibration import LabelEncoder
from xgboost import XGBRegressor
from sklearn.model_selection import GridSearchCV, KFold, train_test_split
import redis
import pandas as pd

def data_read():
    r = redis.Redis(host = 'localhost', port = 16379, db = 0)
    price_keys = r.keys('price_history:*')
    price_keys = [key.decode('utf-8') for key in price_keys]

    all_data = []
    for symbol in price_keys:
        data = reversed(get_redis_data(r, symbol))
        symbol = symbol.replace('price_history:', '')
        for price in data:
            all_data.append({
                'symbol': symbol,
                'price': price
            })
    
    df = pd.DataFrame(all_data)
    return df

def get_redis_data(r, symbol):
    prices = r.lrange(symbol, -1000, -1)
    if prices:
        prices_str = [float(price.decode('utf-8')) for price in prices]
        return prices_str
    
def create_ml_features(df_long):
    """Long format을 ML 학습용으로 변환"""
    
    all_features = []
    
    # 심볼별로 그룹화
    for symbol in df_long['symbol'].unique():
        symbol_data = df_long[df_long['symbol'] == symbol]
        prices = symbol_data['price'].values
        
        # 윈도우 방식으로 특징 생성 (10개 → 1개 예측)
        for i in range(len(prices) - 10):
            features = {
                'symbol': symbol,
                'price_1': prices[i],
                'price_2': prices[i+1], 
                'price_3': prices[i+2],
                'price_4': prices[i+3],
                'price_5': prices[i+4],
                'price_6': prices[i+5],
                'price_7': prices[i+6],
                'price_8': prices[i+7],
                'price_9': prices[i+8],
                'price_10': prices[i+9],
                'target': prices[i+10]
            }
            all_features.append(features)
    
    df_ml = pd.DataFrame(all_features)
    return df_ml

def tune_hyperparameters(data):
    le = LabelEncoder()
    data['symbol_encoded'] = le.fit_transform(data['symbol'])
    
    # 특징 선택 (symbol 제외, symbol_encoded 포함)
    feature_cols = ['symbol_encoded', 'price_1', 'price_2', 'price_3', 
                'price_4', 'price_5', 'price_6', 'price_7', 
                'price_8', 'price_9', 'price_10']

    y = data['target']
    X = data[feature_cols]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y,
        test_size=0.2
    )

    # 하이퍼파라미터 그리드
    param_grid = {
        'booster': ['gbtree'],
        'eta': [0.01, 0.05, 0.1, 0.2],
        'max_depth': [3, 5, 10],
        'min_child_weight': [0.5, 1, 2],
        'gamma': [0, 1, 2, 3],
        'objective': ['reg:linear']
    }
    
    # GridSearchCV 실행
    xgb_model = XGBRegressor()
    cv = KFold(n_splits=6)
    gsc = GridSearchCV(
        xgb_model, 
        param_grid=param_grid, 
        cv=cv, 
        scoring='neg_mean_squared_error', 
        n_jobs=4,
        verbose=2
    )
    
    # 학습 및 최적 파라미터 저장
    gsc.fit(X_train, y_train)
    
    # 최적 모델 저장
    best_model = gsc.best_estimator_
    test_score = best_model.score(X_test, y_test)
    joblib.dump(best_model, 'models/xgboost_best_model.pkl')
    
    print(f"최적 파라미터: {gsc.best_params_}")
    print(f"최적 점수: {gsc.best_score_}")
    print(f'테스트 점수 : {test_score}')

df_long = data_read()
print(df_long.shape)  # (75300, 2) - 251개 코인 × 300개 시점
print(df_long.head())

df_ml = create_ml_features(df_long)
print(f"ML 데이터 크기: {df_ml.shape}")  # (약 72,790, 12)
print(df_ml)

tune_hyperparameters(df_ml)