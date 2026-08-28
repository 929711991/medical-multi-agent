from typing import Any

from fastapi import Request


def get_graph(request: Request) -> Any:
    """读取保存在应用状态中的已编译诊断图。"""
    return request.app.state.diagnosis_graph


def get_ai_job_queue(request: Request) -> Any:
    """读取应用入口注入的 AI 持久任务队列。"""
    return request.app.state.ai_job_queue
