import math

def calculate_sma(data, window):
    if len(data) < window:
        return [None] * len(data)
    sma = []
    for i in range(len(data)):
        if i < window - 1:
            sma.append(None)
        else:
            subset = data[i - window + 1 : i + 1]
            sma.append(sum(subset) / window)
    return sma

def calculate_stddev(data, window, sma):
    if len(data) < window:
        return [None] * len(data)
    stddev = []
    for i in range(len(data)):
        if i < window - 1 or sma[i] is None:
            stddev.append(None)
        else:
            subset = data[i - window + 1 : i + 1]
            variance = sum((x - sma[i]) ** 2 for x in subset) / window
            stddev.append(math.sqrt(variance))
    return stddev

def calculate_ema(data, window):
    if not data:
        return []
    ema = [data[0]]
    alpha = 2 / (window + 1)
    for i in range(1, len(data)):
        ema.append(data[i] * alpha + ema[-1] * (1 - alpha))
    return ema

def calculate_squeeze(data_list, bb_length=20, bb_mult=2, kc_length=20, kc_mult=1.5):
    """
    data_list: [{'price': 100, 'volume': 1000}, ...] 형태의 리스트
    """
    if data_list is None or len(data_list) < max(bb_length, kc_length):
        return None

    # DataFrame이 들어올 경우를 대비해 리스트로 변환 시도
    if hasattr(data_list, 'to_dict'):
        data_list = data_list.to_dict('records')

    try:
        prices = [float(item['price']) for item in data_list]
    except (KeyError, ValueError, TypeError):
        return None
    
    # 1. Bollinger Bands
    sma = calculate_sma(prices, bb_length)
    stddev = calculate_stddev(prices, bb_length, sma)
    
    bb_upper = []
    bb_lower = []
    for i in range(len(prices)):
        if sma[i] is None or stddev[i] is None:
            bb_upper.append(None)
            bb_lower.append(None)
        else:
            bb_upper.append(sma[i] + (bb_mult * stddev[i]))
            bb_lower.append(sma[i] - (bb_mult * stddev[i]))

    # 2. Keltner Channels (간이 ATR 사용)
    tr = [0]
    for i in range(1, len(prices)):
        tr.append(abs(prices[i] - prices[i-1]))
    
    atr = calculate_sma(tr, kc_length)
    ema = calculate_ema(prices, kc_length)
    
    kc_upper = []
    kc_lower = []
    for i in range(len(prices)):
        if ema[i] is None or atr[i] is None:
            kc_upper.append(None)
            kc_lower.append(None)
        else:
            kc_upper.append(ema[i] + (kc_mult * atr[i]))
            kc_lower.append(ema[i] - (kc_mult * atr[i]))

    # 3. Squeeze 상태 및 Momentum
    results = []
    highest_highs = []
    lowest_lows = []
    
    for i in range(len(prices)):
        if i < kc_length - 1:
            highest_highs.append(None)
            lowest_lows.append(None)
        else:
            subset = prices[i - kc_length + 1 : i + 1]
            highest_highs.append(max(subset))
            lowest_lows.append(min(subset))

    for i in range(len(prices)):
        sq_on = False
        if bb_upper[i] is not None and kc_upper[i] is not None:
            sq_on = (bb_upper[i] < kc_upper[i]) and (bb_lower[i] > kc_lower[i])
        
        mom = 0
        if highest_highs[i] is not None and sma[i] is not None:
            mid_line = (highest_highs[i] + lowest_lows[i]) / 2
            mom = prices[i] - ((mid_line + sma[i]) / 2)
            
        res = data_list[i].copy()
        res.update({
            'squeeze_on': sq_on,
            'momentum': mom,
            'sma': sma[i]
        })
        results.append(res)

    return results

def get_squeeze_signal(data_list):
    if not data_list or len(data_list) < 2:
        return "데이터 부족"
        
    latest = data_list[-1]
    prev = data_list[-2]
    
    is_breakout = (prev.get('squeeze_on') == True) and (latest.get('squeeze_on') == False)
    
    if latest.get('squeeze_on'):
        return "Squeeze 진행 중 (에너지 응축)"
    
    if is_breakout:
        if latest.get('momentum', 0) > 0:
            return "🚀 상승 돌파 발생! (매수 추천)"
        else:
            return "⚠️ 하락 돌파 발생! (주의)"
            
    return "관망 (신호 없음)"
