import requests
import json
import sys

# ================= 配置区域 =================
# 如果运行的是 wechat_service.py，通常是 8080
# 如果运行的是 app.py，通常是 5000
BASE_URL = "http://127.0.0.1:8080"


# ===========================================

def print_step(title):
    print(f"\n{'=' * 20} {title} {'=' * 20}")


def test_health_check():
    """测试健康检查接口"""
    print_step("1. 测试健康检查 /health")
    try:
        url = f"{BASE_URL}/health"
        print(f"请求: GET {url}")
        resp = requests.get(url)

        print(f"状态码: {resp.status_code}")
        print("返回内容:", resp.json())

        assert resp.status_code == 200
        print("✅ 健康检查通过")
    except Exception as e:
        print(f"❌ 健康检查失败: {e}")


def test_recommend_json():
    """测试标准 JSON 推荐接口"""
    print_step("2. 测试 API 推荐 /recommend")
    try:
        url = f"{BASE_URL}/recommend"
        payload = {
            "message": "我想听点周杰伦的歌",
            "session_id": "test_script_user_001"
        }

        print(f"请求: POST {url}")
        print(f"参数: {json.dumps(payload, ensure_ascii=False)}")

        resp = requests.post(url, json=payload)

        print(f"状态码: {resp.status_code}")
        data = resp.json()

        # 打印关键信息
        print(f"推荐语: {data.get('recommendation')}")
        songs = data.get('matched_songs', [])
        print(f"匹配歌曲数: {len(songs)}")
        if songs:
            print(f"第一首歌: {songs[0].get('title')} - {songs[0].get('artist')}")

        assert resp.status_code == 200
        assert data.get('success') is True
        print("✅ 推荐接口测试通过")
    except Exception as e:
        print(f"❌ 推荐接口测试失败: {e}")


def test_wechat_message():
    """测试微信消息回调接口 (重点测试对象)"""
    print_step("3. 测试微信消息 /message")
    try:
        url = f"{BASE_URL}/message"
        # 注意：微信接口使用的是 Form Data，不是 JSON
        payload = {
            "from_user": "oGhRu6_test_openid_888",
            "content": "今天很开心",
            "type": "text"
        }

        print(f"请求: POST {url}")
        print(f"参数: {payload}")

        resp = requests.post(url, data=payload)

        print(f"状态码: {resp.status_code}")
        print(f"返回文本: {resp.text}")

        # 微信接口只要接收成功就返回 200 和固定文本
        assert resp.status_code == 200
        assert "正在为您生成音乐推荐" in resp.text

        print("✅ 微信接口请求成功")
        print("⚠️ 注意：此接口为异步处理，请查看服务器控制台日志确认具体的回复内容和歌名列表是否正确拼接。")
    except Exception as e:
        print(f"❌ 微信接口测试失败: {e}")


def test_admin_stats():
    """测试统计接口"""
    print_step("4. 测试统计数据 /stats")
    try:
        # 尝试两个可能的统计地址
        url = f"{BASE_URL}/stats"  # app.py 通用
        resp = requests.get(url)

        if resp.status_code == 404:
            # 可能是 wechat_service 的后台统计
            url = f"{BASE_URL}/admin/stats"
            resp = requests.get(url)

        print(f"请求: GET {url}")
        print(f"状态码: {resp.status_code}")
        if resp.status_code == 200:
            print("统计数据:", json.dumps(resp.json(), indent=2, ensure_ascii=False)[:300] + "...")
            print("✅ 统计接口测试通过")
        else:
            print(f"⚠️ 统计接口返回异常: {resp.status_code}")

    except Exception as e:
        print(f"❌ 统计接口测试失败: {e}")


if __name__ == "__main__":
    print(f"🚀 开始全链路测试 (目标: {BASE_URL})")

    # 按顺序执行测试
    test_health_check()
    test_recommend_json()
    test_wechat_message()
    test_admin_stats()

    print("\n🏁 测试结束")