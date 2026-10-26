"""src/crawler/progress.py — 진행 상황 체크포인트 및 추적기
참고자료(web-crawler/scripts/progress.py) 패턴 구현
"""
import json
import os
import time
from datetime import datetime
from typing import Optional, Dict, Any

class ProgressTracker:
    """작업 진행 상태를 파일에 기록하고 콘솔에 출력하는 추적기"""

    def __init__(self, filepath: str = "output/progress.json", total_steps: int = 4):
        self.filepath = filepath
        self.total_steps = total_steps
        self.current_step = 0
        self.step_name = "초기화"
        self.details: Dict[str, Any] = {}
        self.start_time = time.time()
        os.makedirs(os.path.dirname(filepath) or ".", exist_ok=True)
        self.save()

    def update_step(self, step: int, name: str, details: Optional[Dict[str, Any]] = None):
        """단계 진입 업데이트"""
        self.current_step = step
        self.step_name = name
        if details:
            self.details.update(details)
        self.save()
        elapsed = time.time() - self.start_time
        print(f"\n[Step {step}/{self.total_steps}] {name} (경과: {elapsed:.1f}초)")
        if details:
            for k, v in details.items():
                print(f"  - {k}: {v}")

    def update_detail(self, key: str, value: Any):
        """세부 정보 업데이트"""
        self.details[key] = value
        self.save()

    def save(self):
        """진행 상태 JSON 파일 저장"""
        data = {
            "current_step": self.current_step,
            "total_steps": self.total_steps,
            "step_name": self.step_name,
            "elapsed_seconds": round(time.time() - self.start_time, 2),
            "updated_at": datetime.now().isoformat(),
            "details": self.details,
            "completed": self.current_step >= self.total_steps
        }
        try:
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def complete(self, summary: Optional[str] = None):
        """전체 파이프라인 완료"""
        self.current_step = self.total_steps
        self.step_name = "전체 완료"
        if summary:
            self.details["summary"] = summary
        self.save()
        elapsed = time.time() - self.start_time
        print(f"\n[완료] 모든 파이프라인이 성공적으로 완료되었습니다! (총 소요시간: {elapsed:.1f}초)")
