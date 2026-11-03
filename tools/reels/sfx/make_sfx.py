# 저작권 걱정 없는 효과음을 직접 합성한다 (휙, 톡, 쿵, 띵)
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile
SR = 44100
rng = np.random.default_rng(7)
def save(name, x, pan=None):
    x = x / (np.max(np.abs(x)) + 1e-9) * 0.9
    if pan is None: st = np.stack([x, x], 1)
    else: st = np.stack([x * np.sqrt(1 - pan), x * np.sqrt(pan)], 1)
    wavfile.write(f"{name}.wav", SR, (st * 32767).astype(np.int16))
def env(n, a, r):  # attack/release 비율
    t = np.linspace(0, 1, n); e = np.ones(n)
    e[t < a] = (t[t < a] / a) ** 2; m = t > 1 - r; e[m] = ((1 - t[m]) / r) ** 2; return e
# 휙 (장면 넘김): 대역이 올라갔다 내려가는 바람 소리, 오른쪽→왼쪽
n = int(0.42 * SR); noise = rng.standard_normal(n); out = np.zeros(n); B = 512
for i in range(0, n, B):
    p = i / n; fc = 500 + 3200 * np.sin(np.pi * p) ** 1.5
    sos = butter(2, [fc * 0.6, min(fc * 1.6, 18000)], btype="band", fs=SR, output="sos")
    out[i:i + B] = sosfilt(sos, noise[i:i + B])
w = out * np.sin(np.pi * np.linspace(0, 1, n)) ** 2
L = w * np.linspace(0.35, 1.0, n); R = w * np.linspace(1.0, 0.35, n)
st = np.stack([L, R], 1); st = st / np.max(np.abs(st)) * 0.9
wavfile.write("whoosh.wav", SR, (st * 32767).astype(np.int16))
# 톡 (댓글 등장): 짧게 올라가는 물방울 소리
n = int(0.09 * SR); t = np.arange(n) / SR
f = 650 + 900 * (t / t[-1]); ph = 2 * np.pi * np.cumsum(f) / SR
x = np.sin(ph) * np.exp(-t / 0.028) + 0.15 * np.sin(2 * ph) * np.exp(-t / 0.015)
save("pop", x * env(n, 0.04, 0.3))
# 쿵 (첫 장면): 낮게 떨어지는 울림 + 짧은 타격
n = int(0.7 * SR); t = np.arange(n) / SR
f = 85 * np.exp(-t / 0.35) + 38; ph = 2 * np.pi * np.cumsum(f) / SR
boom = np.sin(ph) * np.exp(-t / 0.22)
hit = sosfilt(butter(2, 1800, fs=SR, output="sos"), rng.standard_normal(n)) * np.exp(-t / 0.018) * 0.6
save("impact", (boom + hit) * env(n, 0.005, 0.2))
# 띵 (결론 장면): 맑은 종소리
n = int(1.1 * SR); t = np.arange(n) / SR
x = sum(a * np.sin(2 * np.pi * fr * t) * np.exp(-t / d) for fr, a, d in [(1318.5, 1, .45), (1975.5, .55, .3), (2637, .3, .2), (659.3, .25, .6)])
save("ding", x * env(n, 0.004, 0.25))
print("ok")
