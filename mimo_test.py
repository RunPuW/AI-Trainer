import asyncio, json, base64, httpx, sys, io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

async def main():
    img_path = r"C:\Users\WWW\Desktop\简历产品.jpg"
    with open(img_path, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode()

    api_key = "tp-ss0r04xczujukwgdiaw73zwk6b79nz1h6f13xcyducjf4fg3"
    api_base = "https://token-plan-sgp.xiaomimimo.com/v1"

    payload = {
        "model": "mimo-v2.5",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "请完整提取这张简历图片中的所有文字内容，包括个人信息、教育背景、项目经历、技能等全部板块，不要遗漏任何信息。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}}
        ]}],
        "max_tokens": 4000,
        "temperature": 0.7
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        resp = await client.post(f"{api_base}/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json=payload)
        result = resp.json()
        if "choices" in result:
            text = result["choices"][0]["message"]["content"]
            with open(r"e:\Personal_trainer\mimo_output.txt", "w", encoding="utf-8") as out:
                out.write(text)
            print("OK")
        else:
            with open(r"e:\Personal_trainer\mimo_output.txt", "w", encoding="utf-8") as out:
                out.write(json.dumps(result, ensure_ascii=False, indent=2))
            print("ERROR")

asyncio.run(main())
