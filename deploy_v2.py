#!/usr/bin/env python3
"""部署到GitHub - 兼容细粒度PAT"""
import urllib.request
import urllib.error
import json
import base64
import os
import sys

TOKEN = os.environ.get("GH_TOKEN", "")
GITHUB_API = "https://api.github.com"
REPO_NAME = "bob-source-collector"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "BOB-Deploy",
    "Authorization": f"Bearer {TOKEN}",
    "X-GitHub-Api-Version": "2022-11-28",
}


def api(method, url, data=None):
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            raw = r.read()
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            err = json.loads(raw)
        except Exception:
            err = {"message": raw.decode(errors="replace")}
        return {"_error": True, "_status": e.code, **err}


def create_repo():
    print("[1/4] 创建仓库...")
    result = api("POST", f"{GITHUB_API}/user/repos", {
        "name": REPO_NAME,
        "description": "BOB全球资讯IP - 信源自动采集（GitHub Actions定时执行）",
        "private": False,
        "auto_init": True,
    })
    if result.get("_error"):
        msg = result.get("message", "")
        if "already exists" in msg.lower() or result.get("_status") == 422:
            print(f"  仓库已存在，复用")
            return True
        print(f"  创建失败: {msg}")
        print(f"  细粒度PAT可能缺少 'Administration' 权限")
        return False
    print(f"  创建成功: {result.get('full_name', '')}")
    return True


def upload_file(path, content, message="deploy"):
    url = f"{GITHUB_API}/repos/wl986/{REPO_NAME}/contents/{path}"
    content_b64 = base64.b64encode(content.encode()).decode()
    data = {"message": message, "content": content_b64, "branch": "main"}

    result = api("PUT", url, data)
    if result.get("_error"):
        if result.get("_status") == 422:
            existing = api("GET", url)
            if existing.get("sha"):
                data["sha"] = existing["sha"]
                result = api("PUT", url, data)
                if not result.get("_error"):
                    return True
        print(f"  上传失败 {path}: {result.get('message', '')}")
        return False
    return True


def trigger_workflow():
    print("[3/4] 触发首次采集...")
    result = api("GET", f"{GITHUB_API}/repos/wl986/{REPO_NAME}/actions/workflows")
    if result.get("_error"):
        print(f"  获取workflow失败: {result.get('message', '')}")
        return False
    workflows = result.get("workflows", [])
    for wf in workflows:
        name = wf.get("name", "")
        if "collect" in name.lower() or "morning" in name.lower():
            trigger = api("POST", f"{GITHUB_API}/repos/wl986/{REPO_NAME}/actions/workflows/{wf['id']}/dispatches", {"ref": "main"})
            if not trigger.get("_error"):
                print(f"  已触发: {name}")
                return True
    print("  未找到可触发的workflow，请稍后在GitHub Actions页面手动触发")
    return False


def main():
    if not TOKEN:
        print("错误: 未设置 GH_TOKEN 环境变量")
        return

    # Step 1: Create repo
    if not create_repo():
        print("\n方案B: 尝试用git方式部署...")
        # Initialize local git and try to push
        os.system("git init")
        os.system("git config user.name 'BOB Collector'")
        os.system("git config user.email 'collector@bob.local'")
        os.system("git add -A")
        os.system('git commit -m "BOB信源采集系统部署"')
        remote_url = f"https://wl986:{TOKEN}@github.com/wl986/{REPO_NAME}.git"
        os.system(f"git remote add origin {remote_url} 2>/dev/null || git remote set-url origin {remote_url}")
        result = os.system(f"git push -u origin main 2>&1")
        if result != 0:
            print("\ngit push也失败了。请手动创建仓库:")
            print(f"  1. 打开 https://github.com/new")
            print(f"  2. 仓库名: {REPO_NAME}")
            print(f"  3. 设为Public，勾选 Add README")
            print(f"  4. 创建后告诉我，我重新推送")
            return
        print("  git push成功!")
    else:
        # Step 2: Upload files
        print("[2/4] 上传文件...")
        script_dir = os.path.dirname(os.path.abspath(__file__))
        files = [
            ("collect_sources.py", os.path.join(script_dir, "collect_sources.py")),
            (".github/workflows/collect-morning.yml", os.path.join(script_dir, ".github", "workflows", "collect-morning.yml")),
            (".github/workflows/collect-evening.yml", os.path.join(script_dir, ".github", "workflows", "collect-evening.yml")),
        ]
        for gh_path, local_path in files:
            try:
                with open(local_path, 'r') as f:
                    content = f.read()
                ok = upload_file(gh_path, content)
                print(f"  {'OK' if ok else 'FAILED'}: {gh_path}")
            except FileNotFoundError:
                print(f"  SKIP: {local_path} not found")

    # Step 3: Trigger workflow
    trigger_workflow()

    # Step 4: Output
    raw_url = f"https://raw.githubusercontent.com/wl986/{REPO_NAME}/main/latest_sources.md"
    print(f"\n[4/4] 部署完成!")
    print(f"  仓库: https://github.com/wl986/{REPO_NAME}")
    print(f"  Actions: https://github.com/wl986/{REPO_NAME}/actions")
    print(f"  数据URL: {raw_url}")


if __name__ == "__main__":
    main()
