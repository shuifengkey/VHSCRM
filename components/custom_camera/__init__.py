import os
import streamlit.components.v1 as components

_component_func = components.declare_component(
    "custom_camera",
    path=os.path.join(os.path.dirname(__file__), "frontend")
)

def custom_camera(key=None):
    component_value = _component_func(key=key, default=None)
    return component_value