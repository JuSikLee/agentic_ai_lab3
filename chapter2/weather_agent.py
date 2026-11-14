# 라이브러리 임포트
import os
import json
import requests
from dotenv import load_dotenv
from anthropic import Anthropic
load_dotenv()         # 환경 변수 로딩
client = Anthropic()  # Anthropic 클라이언트 초기화

# 도시 이름을 받아 현재 날시를 반환하는 get_weather 함수 작성
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

# 날씨 툴의 JSON 스키마
tools = [
	{
		'name': 'get_weather',
		'description': '도시의 현재 날씨를 조회합니다.',
		'input_schema': {
			'type': 'object',
			'properties': {
				'city': {
					'type': 'string',
					'description': '날씨를 조회할 도시 이름 (영문)',
				}
			},
			'required': ['city'],
		},
	}
]

"""에이전트를 실행하는 함수"""
def run_agent(user_message):
	print(f'사용자: {user_message}')
	
	# 시스템 프롬프트와 LLM에 전달하는 기본 메시지
	system_prompt = '당신은 날씨 정보를 알려주는 도우미입니다.'
	messages = [
		{'role': 'user', 'content': user_message},
	]
	# 1. LLM에 질문 + 툴 목록 전송
	response = client.messages.create(
		model='claude-sonnet-5',
		max_tokens=1024,
		system=system_prompt,
		messages=messages,
		tools=tools,
	)
	
	# 2. 툴 호출이 있는지 확인 (stop_reason)
	if response.stop_reason == 'tool_use':
		# 툴 호출이 포함된 응답을 페이지에 추가
		messages.append({'role': 'assistant', 'content': response.content})
		tool_results = []
		for block in response.content:
			if block.type != 'tool_use':
				continue
			name = block.name
			args = block.input      # 이미 dick 형태 (json.loads 불필요)
			print(f'툴 호출: {name}({args})')
			# 3. 실제 함수를 실행
			result = get_weather(**args)
			print(f'툴 결과: {result}')
			# 4. 함수 실행 결과를 모은다
			tool_results.append({
				'type': 'tool_result',
				'tool_use_id': block.id,
				'content': result,
        })
		# 툴 결과를 user 메시지로 전달
		messages.append({'role': 'user', 'content': tool_results})
		# 5. LLM이 최종 답변 생성
		final = client.messages.create(
			model='claude-sonnet-5',  # 모델명
			max_tokens=1024,          # 출력 최대 토큰 수
			system=system_prompt,
			messages=messages,
		)
		answer = final.content[0].text
	else:
		# 툴 호출 없이 바로 답변한 경우
		answer = response.content[0].text
	print(f'에이전트: {answer}')
	return answer

if __name__ == "__main__":
	run_agent('안녕하세요')