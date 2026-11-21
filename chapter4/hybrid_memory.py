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

class HybridTokenMemory:
	def __init__(self, threshold=4000, model="claude-sonnet-5"):
		self.threshold = threshold
		self.model = model
		self.messages = []     # Sliding window: 최근 대화 원문
		self.summary = None    # Summary: 이전 대화들의 압축본
		self.system_prompt = "당신은 친절한 AI 비서입니다."
	def get_system(self) -> str:
		"""요약을 표함한 시스템 프롬프트를 반환한다."""
		if self.summary:
			return (f"{self.system_prompt}\n\n" f"이것은 이전 대화의 요약이다: {self.summary}")
		return self.system_prompt
	def _count_tokens(self, msgs: list[dict]) -> int:
		"""Anthropic count_tokens API로 메시지 목록을 총 토큰 수를 계산한다."""
		if not msgs:
			return 0
		response = client.messages.count_tokens(
			model=self.model,
			system=self.get_system(),
			messages=msgs,
		)
		return response.input_tokens
	def add_message(self, role, content):
		"""새 메시지를 추가하고, 임계값을 넘으면 요약 프로세스를 실행한다."""
		self.messages.append({"role": role, "content": content})
		# 현재 전체 토큰(시스템 프롬프트 + 요약본 + 대화 리스트) 계산
		# [수정] 기존에는 이 줄만 공백(스페이스 8칸)으로 들여쓰기 되어 있어 TabError(탭/공백 혼용 오류)가 발생함 -> 탭(\t\t)으로 통일
		current_tokens = self._count_tokens(self.messages)
		if current_tokens > self.threshold:
			self._compress_memory()
	def _compress_memory(self):
		"""임계값 초과 시, 앞부분 메시지의 절반을 요약본에 합치고 리스트에서 제거한다."""
		mid = len(self.messages) // 2
		# 클로드는 user 메시지로 시작해야 하므로 분할 지점을 user 메시지에 맞춘다
		while mid < len(self.messages) and self.messages[mid]["role"] != "user":
			mid += 1
		to_summarize = self.messages[:mid]
		self.messages = self.messages[mid:]  # 슬라이딩 윈도우 적용 (절반 제거)
		text_to_sum = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])
		print("\n[시스템] 토큰 한도 초과로 인한 요약 업데이트 중...")
		# Claude를 사용하여 기존 요약과 새 대화를 병합 요약
		response = client.messages.create(
			model=self.model,
			max_tokens=1024,
			system="당신은 대화의 핵심 맥락과 중요한 정보(이름, 장소, ""결정사항)를 저장하는 요약 전문가입니다.",
			messages=[
				{"role": "user", "content": f"기존 요약: {self.summary}\n" f"추가된 대화:\n{text_to_sum}\n\n" "위 내용을 함쳐서 하나의 간졀한 요약으로 만들어주세요."}
			]
		)
		self.summary = "".join(
			b.text for b in response.content if b.type == "text"
		)
	def get_messages(self):
		"""Claude에 전달할 최근 대화 메시지 리스트"""
		# 요약은 get_system()의 시스템 프롬프트에 포함되며,
		# 최근 상세 대화(Sliding Window)만 messages로 전달한다
		return self.messages

def chat_with_hybrid_memory():
	"""하이브리드 메모리(슬라이딩 윈도우 + 요약) 챗봇"""
	# 1. 메모리 초기화 - threshold를 작게 잡으면 짧은 대화에서 요약 관찰 가능
	memory = HybridTokenMemory(threshold=2000)
	print("하이브리드 메모리 챗봇입니다. (종료: quit)")
	while True:
		user_input = input("\n사용자: ")
		if user_input.lower() == "quit":
			break
		# 2. 사용자 메시지 추가
		memory.add_message("user", user_input)
		# 3. Claude 호출
		response = client.messages.create(
			model="claude-sonnet-5",
			max_tokens=1024,
			system=memory.get_system(),
			messages=memory.get_messages()   # 슬라이딩 윈도우에 있는 최근 대화 원문
		)
		assistant_msg = "".join(
			b.text for b in response.content if b.type == "text"
		)
		# 4. AI 응답도 메모리에 저장 - 응답이 추가되면서 다시 임계값을 넘으면
		# 자동으로 요약
		memory.add_message("assistant", assistant_msg)
		print(f"\nAI: {assistant_msg}")
		# 5. 현재 메모리 상태를 표시해서 슬라이딩/요약 동작을 눈으로 확인
		if memory.summary:
			print(f"  [요약 존재: {len(memory.summary)}자]")
		print(f"  [활성 메시지: {len(memory.messages)}개]")
if __name__ == "__main__":
	chat_with_hybrid_memory()