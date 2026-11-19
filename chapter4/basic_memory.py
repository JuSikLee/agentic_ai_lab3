import os
from anthropic import Anthropic
from dotenv import load_dotenv
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
	raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
client = Anthropic(api_key=api_key)   # .env에 작성된 ANTHROPIC_API_KEY 환경 변수 자동 로드
# 시스템 프롬프트는 messages 리스트와 분리해서 관리한다.
SYSTEM_PROMPT = "당신은 친절한 AI 비서입니다."
def chat_with_memory():
	"""단기 메모리가 있는 챗봇"""
	# 1. 메시지 저장소 - 사용자 대화와, AI 응답을 모두 저장
	messages = []
	print("대화를 시작합니다. (종료: quit)")
	while True:
		user_input = input("\n사용자: ")
		if user_input.lower() == "quit":
			break
		# 2. 사용자 메시지 저장
		messages.append({"role": "user", "content": user_input})
		# 3. 저장소에 있는 모든 내용으로 API 호출
		response = client.messages.create(
			model="claude-sonnet-5",
			max_tokens=1024,
			system=SYSTEM_PROMPT,
			messages=messages
		)
		assistant_msg = "".join(
			b.text for b in response.content if b.type == "text"
		)
		# 4. AI 응답 저장
		messages.append({"role": "assistant", "content": assistant_msg})
		print(f"\nAI: {assistant_msg}")
if __name__ == "__main__":
	chat_with_memory()