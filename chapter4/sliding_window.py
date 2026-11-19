import os
from pathlib import Path
from anthropic import Anthropic
from dotenv import load_dotenv

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
client = Anthropic(api_key=api_key)
SYSTEM_PROMPT = "당신은 친절한 AI 비서입니다."
def count_tokens(messages: list[dict], system: str = SYSTEM_PROMPT) -> int:
	"""Anthropic의 count_tokens API로 메시지 목록의 총 토큰 수를 계산한다."""
	if not messages:
		return 0
	response = client.messages.count_tokens(
		model="claude-sonnet-5",
		system=system,
		messages=messages,
	)
	return response.input_tokens
def sliding_window_memory(
	messages: list[dict],
	max_tokens: int = 4000,
	system: str = SYSTEM_PROMPT
) -> list[dict]:
	"""최근 메시지만 유지하되, 토큰 한도를 넘지 않도록 조절한다."""
	# 전체 메시지가 한도 이내라면 그래로 사용
	if count_tokens(messages, system) <= max_tokens:
		return messages
	# ---- 핵심 코드 ----------
	# 한도를 넘으면, user 메시지에서 시작하는 가장 긴 최근 구간을 찾음
	# (클로드는 messages가 user 메시지로 시작)
	for start in range(1, len(messages)):
		if messages[start]["role"] != "user":
			continue
		window = messages[start:]
		if count_tokens(window, system) <= max_tokens:
			return window
	# ---- 핵심 코드 ----------
	return messages[-1:]