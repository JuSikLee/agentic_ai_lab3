import re
import json
import os
import requests
from pathlib import Path
from dotenv import load_dotenv
from anthropic import Anthropic

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
ENV_PATH = PROJECT_ROOT / ".env"
load_dotenv(dotenv_path=ENV_PATH, override=True)
api_key = os.getenv("ANTHROPIC_API_KEY")
if not api_key:
    raise RuntimeError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
client = Anthropic(api_key=api_key)

# 날씨 툴
def get_weather(city: str) -> str:
	"""도시의 현재 날씨를 조회한다."""
	api_key = os.getenv('WEATHER_API_KEY')
	url = 'http://api.openweathermap.org/data/2.5/weather'
	params = {
		'q' : city,
		'appid' : api_key,
		'units': 'metric',   # 섭씨
		'lang' : 'kr'        # 한국어
	}

	# 2. requests로 날씨 정보 받기
	response = requests.get(url, params=params)
	data = response.json()

	# 3. 받은 정보 분석
	if response.status_code != 200:
		 return f'날씨 조회 실패: {data.get("message", "알 수 없는 오류")}'

	# 4. 결괏값 반환
	return json.dumps({
		'city': city,
		'temp': data['main']['temp'],
		'description': data['weather'][0]['description'],
		'humidity': data['main']['humidity'],
	}, ensure_ascii=False)

# 계산 툴
def calculate(expression: str) -> str:
	"""수학 계산식을 계산한다."""
	try:
		result = eval(expression, {"__builtins__": None}, {})
		return json.dumps({'expression': expression, 'result': result})
	except Exception as e:
		return json.dumps({'error': str(e)})

# 커스텀 툴 스키마
TOOLS = {
	'get_weather': {
		'func': get_weather,
		'description': '도시의 기온, 날씨, 습도를 조회합니다.',
		'parameters': {'city': '영문 도시 이름 (예: Seoul, Tokyo)'},
	},
	'calculate': {
		'func': calculate,
		'description': '수학식을 계산합니다.',
		'parameters': {'expression': '계산할 수식 (예: 2+3*4)'},
	},
}

# 툴 목록을 시스템 프롬프트에 포함
def build_tool_description() -> str:
	lines = ["사용 가능한 툴:"]
	for name, info in TOOLS.items():
		lines.append(f"- {name}: {info['description']}")
		lines.append(f"  파라미터: {info['parameters']}")
	return '\n'.join(lines)
SYSTEM_PROMPT = f"""당신은 유능한 AI 에이전트입니다. 사용자의 질문에 답하기 위해 툴을 사용할 수 있습니다.
{build_tool_description()}
**응답 규칙:**
1. 반드시 JSON 형식으로만 응답하십시요.
2. 정보가 부족하여 툴이 필요하다면 'action' 형식을 사용합니다.
3. 툴 결과(Observation)를 확인한 후 답변이 가능하다면 'answer' 형식을 사용합니다.
4. 마크다운 코드 블록(```)을 절대 사용하지 마십시오. JSON 객체 하나만, 다른 텍스트 없이 출력하십시오.
**JSON 응답 형식:**
1) 툴 호출 시:
{{"thought": "상황 분석", "action": "툴_이름", "action_input": {{"매개변수명": "값"}}}}
2) 최종 답변 시:
{{"thought": 최종 분석", "answer": "사용자에게 전달할 답변"}}"""

def parse_llm_response(text: str) -> dict:
	# LLM API 의 흔한 오류 ```json ... ``` 또는 ``` ... ``` 제거
	fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
	if fenced:
		text = fenced.group(1)
	else:
		# 본문 중 첫 번째 { ... } 블록만 추출
		match = re.search(r"\{.*\}", text, re.DOTALL)
		if match:
			text = match.group(0)
	try:
		return json.loads(text)
	except json.JSONDecodeError:
		return {"thought": "Parsing failed", "answer": text}

def run_react_json_agent(user_message: str, max_iterations: int = 5):
	print(f'\n{"="*50}')
	print(f'사용자: {user_message}')
	print('='*50)
	messages = [
		{'role': 'user', 'content': user_message},
	]
	for i in range(max_iterations):
		# Claude 모델을 호출
		response = client.messages.create(
			model='claude-sonnet-5',
			max_tokens=1024,
			system=SYSTEM_PROMPT,
			messages=messages,
		)
		# 응답에서 텍스트 블록만 추출
		raw_content = ''.join(b.text for b in response.content if b.type == 'text')
		parsed = parse_llm_response(raw_content)
		thought = parsed.get('thought', '')
		if thought:
			print(f'\n[Thought] {thought}')
		# 최종 답변인 경우
		if 'answer' in parsed:
			print(f'\n[Answer] {parsed["answer"]}')
			return parsed['answer']
		# 툴 호출인 경우
		action = parsed.get('action')
		action_input = parsed.get('action_input', {})
		if action in TOOLS:
			print(f'[Action] {action}({action_input})')
			# 툴 실행
			tool_func = TOOLS[action]['func']
			try:
				result = tool_func(**action_input)
			except Exception as e:
				result = f"Error executing tool: {str(e)}"
			print(f'[Observation] {result}')
			# 대화 기록 업데이트
			messages.append({'role': 'assistant', 'content': raw_content})
			messages.append({
				'role': 'user',
				'content': f"Observation: {result}\n\n위 결과를 바탕으로 다음 단계 (추가 툴 호출 또는 최종 답변)를 진행하세요."
			})
		else:
		    print(f'[Error] 알 수 없는 툴: {action}')
		    break
	print('\n[경고] 최대 반복 횟수에 도달했습니다.')

# 복잡한 질문
run_react_json_agent('서울과 도쿄 기온 차이를 계산해줘')