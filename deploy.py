#!/usr/bin/env python3
"""
一键部署到GitHub - 用户提供Personal Access Token即可自动创建仓库+上传文件
用法: python3 deploy.py YOUR_GITHUB_TOKEN
"""

import urllib.request
import urllib.error
import json
import base64
import os
import sys

GITHUB_API = "https://api.github.com"
REPO_NAME = "bob-source-collector"


def api_call(url, method="GET", token=None, data=None):
    """调用GitHub API"""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "BOB-Deploy-Script",
    }
    if token:
        headers["Authorization"] = f"token {token}"
    if data:
        headers["Content-Type"] = "application/json"

    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return json.loads(response.read()) if response.read() else {}
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = json.loads(e.read()).get("message", "")
        except Exception:
            pass
        return {"_error": True, "_status": e.code, "_message": error_body}


def create_repo(token):
    """创建GitHub仓库（公开）"""
    result = api_call(f"{GITHUB_API}/user/repos", "POST", token, {
        "name": REPO_NAME,
        "description": "BOB全球资讯IP - 信源自动采集（GitHub Actions定时执行，无需开机）",
        "private": False,
        "auto_init": True,
    })

    if result.get("_error"):
        if result["_status"] == 422:
            print(f"  仓库 {REPO_NAME} 已存在，将复用")
            # 获取用户信息
            user = api_call(f"{GITHUB_API}/user", "GET", token)
            owner = user.get("login", "")
            return f"{owner}/{REPO_NAME}", f"https://github.com/{owner}/{REPO_NAME}", "main"
        else:
            print(f"  创建仓库失败: {result['_message']}")
            return None, None, None

    full_name = result.get("full_name", "")
    html_url = result.get("html_url", "")
    branch = result.get("default_branch", "main")
    return full_name, html_url, branch


def upload_file(token, full_name, path, content, branch="main", message="Initial upload"):
    """上传文件到GitHub仓库"""
    url = f"{GITHUB_API}/repos/{full_name}/contents/{path}"
    content_b64 = base64.b64encode(content.encode()).decode()

    data = {
        "message": message,
        "content": content_b64,
        "branch": branch,
    }

    result = api_call(url, "PUT", token, data)

    if result.get("_error"):
        if result["_status"] == 422:
            # 文件已存在，获取sha后更新
            existing = api_call(url, "GET", token)
            if existing.get("sha"):
                data["sha"] = existing["sha"]
                result = api_call(url, "PUT", token, data)
                if not result.get("_error"):
                    return True
            print(f"  更新失败 {path}: {result.get('_message', '')}")
            return False
        else:
            print(f"  上传失败 {path}: {result.get('_message', '')}")
            return False

    return True


def trigger_workflow(token, full_name):
    """手动触发一次workflow测试"""
    # 获取workflow列表
    result = api_call(f"{GITHUB_API}/repos/{full_name}/actions/workflows", "GET", token)
    if result.get("_error"):
        return False

    workflows = result.get("workflows", [])
    for wf in workflows:
        if "morning" in wf.get("name", "").lower() or "collect" in wf.get("name", "").lower():
            # 触发workflow
            trigger_url = f"{GITHUB_API}/repos/{full_name}/actions/workflows/{wf['id']}/dispatches"
            trigger_result = api_call(trigger_url, "POST", token, {
                "ref": "main",
                "inputs": {},
            })
            if not trigger_result.get("_error"):
                print(f"  已触发: {wf['name']}")
                return True
    return False


def main():
    print("=" * 50)
    print("BOB信源采集 - GitHub一键部署")
    print("=" * 50)

    token = os.environ.get("GITHUB_TOKEN") or (sys.argv[1] if len(sys.argv) > 1 else "")

    if not token:
        print("\n请提供GitHub Personal Access Token")
        print("\n生成步骤:")
        print("  1. 打开 https://github.com/settings/tokens")
        print("  2. 点击 'Generate new token (classic)'")
        print("  3. Note: bob-collector")
        print("  4. 勾选权限: repo")
        print("  5. 生成后复制token")
        print("\n运行: python3 deploy.py ghp_你的token")
        return

    # Step 1: 创建仓库
    print(f"\n[1/4] 创建仓库 {REPO_NAME}...")
    full_name, html_url, branch = create_repo(token)
    if not full_name:
        print("部署失败")
        return

    owner = full_name.split("/")[0]
    print(f"  仓库: {html_url}")

    # Step 2: 读取本地文件
    script_dir = os.path.dirname(os.path.abspath(__file__))
    files_to_upload = [
        ("collect_sources.py", os.path.join(script_dir, "collect_sources.py")),
        (".github/workflows/collect-morning.yml", os.path.join(script_dir, ".github", "workflows", "collect-morning.yml")),
        (".github/workflows/collect-evening.yml", os.path.join(script_dir, ".github", "workflows", "collect-evening.yml")),
    ]

    # 读取文件内容
    file_contents = []
    for github_path, local_path in files_to_upload:
        try:
            with open(local_path, 'r') as f:
                file_contents.append((github_path, f.read()))
        except FileNotFoundError:
            print(f"  [警告] 文件不存在: {local_path}")

    # Step 3: 上传文件
    print(f"\n[2/4] 上传 {len(file_contents)} 个文件...")
    for github_path, content in file_contents:
        print(f"  上传 {github_path}...", end=" ")
        if upload_file(token, full_name, github_path, content, branch, "BOB信源采集系统部署"):
            print("OK")
        else:
            print("FAILED")

    # Step 4: 触发首次采集
    print(f"\n[3/4] 触发首次采集测试...")
    if trigger_workflow(token, full_name):
        print("  首次采集已触发，约2-3分钟后查看结果")
    else:
        print("  手动触发失败，可稍后在GitHub Actions页面手动触发")

    # 输出配置信息
    raw_url = f"https://raw.githubusercontent.com/{full_name}/{branch}/latest_sources.md"
    print(f"\n[4/4] 部署完成!")
    print(f"\n{'=' * 50}")
    print(f"仓库地址: {html_url}")
    print(f"Actions页面: {html_url}/actions")
    print(f"数据读取URL: {raw_url}")
    print(f"GitHub用户名: {owner}")
    print(f"{'=' * 50}")
    print(f"\n接下来:")
    print(f"  1. 首次采集完成后，latest_sources.md将自动生成")
    print(f"  2. 每天北京时间 8:00 和 20:00 自动采集")
    print(f"  3. 电脑关机也不影响，完全在GitHub云端执行")
    print(f"  4. 告诉我你的GitHub用户名，我来配置WorkBuddy自动读取")


if __name__ == "__main__":
    main()
