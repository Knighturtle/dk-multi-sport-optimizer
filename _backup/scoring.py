# pyright: reportUndefinedVariable=false
# --- compatibility shim for expected_fp ---

from typing import Callable, Any, Optional

# このモジュール内に実装があると想定される候補名
_CANDIDATES = (
    "expected_points",
    "expected_fantasy_points",
    "calc_expected_fp",
    "predict_expected_fp",
)

_expected_impl: Optional[Callable[..., Any]] = None
for _name in _CANDIDATES:
    func = globals().get(_name)
    if callable(func):
        _expected_impl = func
        break

def expected_fp(*args: Any, **kwargs: Any):
    """
    互換API。実体（上記候補のいずれか）が存在すればそれを呼ぶ。
    無ければ明示的に例外を投げて知らせる。
    """
    if _expected_impl is None:
        raise NotImplementedError(
            "expected_fp is not wired. Implement one of "
            f"{_CANDIDATES} in src/scoring.py or import it here."
        )
    return _expected_impl(*args, **kwargs)
