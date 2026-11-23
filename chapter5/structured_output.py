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
# Anthropic
tools = [
	{
		"name": "restaurant_recommendations",
		"description": "추천 맛집 목록을 구조화된 형식으로 반환합니다.",
		"input_schema": {
			"type": "object",
			"properties": {
				"restaurants": {
					"type": "array",
					"items": {
						"type": "object",
						"properties": {
							"name": {"type": "string"},
							"cuisine": {"type": "string"},
                            "reason": {"type": "string"}
						},
						"required": ["name", "cuisine", "reason"]
					}
				}
			},
			"required": ["restaurants"]
		}
	}
]
response = client.messages.create(
	model="claude-sonnet-5",
	max_tokens=1024,
	system="맛집 정보를 제공합니다.",
	messages=[
		{"role": "user", "content": "서울의 맛집 3곳 추천해줘"}
	],
	tools=tools,
	# tool_choice로 특정 툴을 강제하면 스키마에 가까운 출력을 보장)
	tool_choice={"type": "tool", "name": "restaurant_recommendations"}
)
# tool_use 블록의 input이 곧 스키마에 맞는 구조화된 데이터
data = next(b.input for b in response.content if b.type == "tool_use")
for r in data["restaurants"]:
	print(f"{r['name']} ({r['cuisine']}): {r['reason']}")