import os
import sys
import streamlit.components.v1 as components

# Ensure the VHSCRM root is always on sys.path so this component resolves correctly
# whether running locally or on Streamlit Cloud (/mount/src/vhscrm)
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _root not in sys.path:
    sys.path.insert(0, _root)

_COMPONENT_NAME = "custom_camera"
_FRONTEND_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "frontend_v2")

_component_func = components.declare_component(
    _COMPONENT_NAME,
    path=_FRONTEND_DIR,
)

def custom_camera(key=None, height=520):
    """
    Render an embedded document scanner with live edge detection.
    Uses OpenCV.js client-side for:
      - Realtime document boundary detection (Canny + Contour)
      - Perspective warp (top-down correction)
      - Enhancement (CLAHE / Adaptive Threshold)

    Returns a JPEG data-URL string when the user clicks "Dùng ảnh này",
    or None while the user is still viewing/retaking.
    """
    return _component_func(key=key, default=None, height=height)