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
	# 1. 메시지 저장소 - 사용자 대화와, AI 응답을 모두 저장
	#    (Anthropic은 system을 별도 파라미터로 받으므로 messages에 포함하지 않음)
	messages = []
	print("대화를 시작합니다. (종료: quit)")
	while True:
		user_input = input("\n사용자: ")
		if user_input.lower() == "quit":
			break
		# 2. 사용자 메시지 저장
		messages.append({"role": "user", "content": user_input})
		# 3. 슬라이딩 윈도우 적용 (예시로 500토큰 제한 설정)
		#    실제 환경에서는 모델의 context window에 맞춰 200000 이하로 설정
		windowed_history = sliding_window_memory(
			messages=messages,
			max_tokens=500,
			system=SYSTEM_PROMPT
		)
		# 4. 슬라이딩된 메시지로 API 호출
		response = client.messages.create(
			model="claude-sonnet-5",
			max_tokens=1024,
			system=SYSTEM_PROMPT,
			messages=windowed_history
		)
		assistant_msg = "".join(
			b.text for b in response.content if b.type == "text"
		)
		# 5. AI 응답 저장
		messages.append({"role": "assistant", "content": assistant_msg})
		print(f"\nAI: {assistant_msg}")
if __name__ == "__main__":
	chat_with_memory()