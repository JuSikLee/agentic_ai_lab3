import os
import json
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
load_dotenv()
client = Anthropic()
REACT_SYSTEM_PROMPT = """
당신은 툴을 사용할 수 있는 AI 에이전트 입니다. 반드시 다음 형식을 따릅니다.
Thought: 지금까지 알아낸 것과 아직 부족한 정보를 한두 문장으로 분석합니다.
Action: 그 판단에 따라 필요한 툴을 호출합니다.
Observation: 툴 실행 결과이며, 시스템이 제공합니다.
툴을 호출하기 전에는 반드시 Thought를 텍스트로 먼저 출력합니다.
Observation은 직접 지어내지 말고 시스템이 준 값만 사용합니다.
Observation을 받으면 다시 Thought로 돌아가 위 과정을 반복합니다.
충분한 정보가 모이면 Thought 없이 최종 답변만 출력한다."""

# ------------------------
# 툴 함수와 스키마
# ------------------------

# 날씨 툴
def get_weather(city: str) -> str:
    # 1. 날씨 api 설정하기
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

# 계산기 툴
def calculate(expression: str) -> str:
	"""수학 계산식을 계산한다."""
	try:
		result = eval(expression, {'__builtins__': {}})
		return json.dumps({'expression': expression, 'result': result})
	except Exception as e:
		return json.dumps({'error': str(e)})
		
# 툴 매핑
tool_map = {
	'get_weather': get_weather,
	'calculate': calculate,
}

# 툴 스키마 (Anthropic 형식)
tools = [
	{
		'name': 'get_weather',
		'description': '도시의 현재 기온, 날씨 상태, 습도를 조회합니다.',
		'input_schema': {
			'type': 'object',
			'properties': {
				'city': {'type': 'string',
				'description': '영문 도시 이름 (예: Seoul, Tokyo)'}
			},
			'required': ['city'],
		},
	},
	{
		'name': 'calculate',
		'description': '수학 계산식을 평가합니다. 사칙연산, 거듭제곱을 지원합니다.',
		'input_schema': {
			'type': 'object',
			'properties': {
				'expression': {'type': 'string',
				'description': '계산할 수식 (예: 2+3*4)'}
			},
			'required': ['expression'],
		},
	},
]

# ------------------------
# ReAct 실행 루프 구현
# ------------------------
def run_react_agent(user_message, max_iterations=5):
	print(f'\n{"="*50}')
	print(f'사용자: {user_message}')
	print('='*50)
	messages = [
		{'role': 'user', 'content': user_message},
	]
	for i in range(max_iterations):
		response = client.messages.create(
			model='claude-sonnet-5',
			max_tokens=1024,
			system=REACT_SYSTEM_PROMPT,
			messages=messages,
			tools=tools,
		)
		# Thought 출력 (LLM이 생성한 텍스트 블록)
		thought = ''.join(b.text for b in response.content if b.type == 'text')
		if thought:
			print(f'\n[Thought] {thought}')
		# 툴 호출이 없으면 최종 답변
		if response.stop_reason != 'tool_use':
			print(f'[Answer] {thought}')
			return thought
		# Action: 툴 호출 가져오기
		messages.append({'role': 'assistant', 'content': response.content})
		tool_results = []
		for block in response.content:
			if block.type != 'tool_use':
				continue
			# 선택된 툴 이름
			name = block.name
			args = block.input
			print(f'[Action] {name}({args})')
			# 툴 실행
			result = tool_map[name](**args)
			print(f'[Observation] {result}')
			# 결과를 모은다
			tool_results.append({
				'type': 'tool_result',
				'tool_use_id': block.id,
				'content': result
			})
		# 툴 결과를 user 메시지로 전달
		messages.append({'role': 'user', 'content': tool_results})
	print('\n[경고] 최대 반복 횟수에 도달했습니다.')
	return '죄송합니다. 처리 중 문제가 발생했습니다.'

# 복잡 질문: 툴 두 개 + 추론
run_react_agent('뉴욕 날씨를 섭씨에서 화씨로 변환해줘')