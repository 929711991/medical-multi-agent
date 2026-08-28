from typing import Any

from fastapi import Request


def get_graph(request: Request) -> Any:
    """读取保存在应用状态中的已编译诊断图。"""
    return request.app.state.diagnosis_graph
