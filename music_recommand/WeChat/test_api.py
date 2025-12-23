import requests
import json

# 定义一个以 test_ 开头的函数，PyCharm 就能识别到了
def test_recommend_flow():
    BASE_URL = "http://127.0.0.1:5000"  # 确保这里端口是 5000

    print("\n--- 开始测试 ---")

    # 1. 测试基础推荐
    try:
        print(f"正在连接 {BASE_URL}/recommend ...")
        response = requests.post(
            f"{BASE_URL}/recommend",
            json={"message": "朴树", "session_id": "test_user_001"}
        )
        print("推荐接口状态码:", response.status_code)
        # 只要没有报错，pytest 就认为测试通过
        assert response.status_code == 200
        print("推荐结果:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    except Exception as e:
        print("推荐接口连接失败:", e)
        assert False  # 强制让测试失败
    #
    # # 2. 测试模拟微信消息
    # try:
    #     print(f"\n正在连接 {BASE_URL}/message ...")
    #     response = requests.post(
    #         f"{BASE_URL}/message",
    #         data={
    #             "from_user": "mock_user_007",
    #             "content": "推荐一些悲伤的歌",
    #             "type": "text"
    #         }
    #     )
    #     print("微信接口返回:", response.text)
    #     assert response.status_code == 200
    # except Exception as e:
    #     print("微信接口连接失败:", e)