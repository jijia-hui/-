from celery import shared_task
from .models import Submission
import docker

@shared_task
def run_code_check(submission_id):
    """评测任务（Docker 执行）"""
    submission = Submission.objects.get(id=submission_id)
    submission.status = 'running'
    submission.save()

    try:
        # 这里写 Docker 评测逻辑（省略具体实现）
        # 示例：调用 docker 运行代码并比对测试用例
        client = docker.from_env()
        # ... 执行代码，获取输出，计算得分
        output = "评测结果示例"
        score = 100
        status = 'success'
        submission.output = output
        submission.score = score
        submission.status = status
    except Exception as e:
        submission.status = 'error'
        submission.output = str(e)
    finally:
        submission.save()