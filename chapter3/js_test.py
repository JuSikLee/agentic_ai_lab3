while True:
    # 사용자에게 문자열 입력받기
    user_input = input("명령어를 입력하세요 (종료: quit): ")

    # 사용자가 quit를 입력했는지 검사
    if user_input.lower() == "quit":
        print("프로그램을 종료합니다.")
        break

    # quit가 아니라면 계속 실행
    print(f"입력한 명령어: {user_input}")

print("반복문 종료 완료")