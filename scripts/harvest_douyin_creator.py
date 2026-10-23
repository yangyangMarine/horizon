#!/usr/bin/env python3
"""
harvest_douyin_creator.py
Tool to extract video URLs and titles from a Douyin creator homepage.
Supports automated extraction via yt-dlp or generates a browser console harvester.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Browser JavaScript snippet for 100% reliable zero-block extraction
BROWSER_HARVESTER_JS = """
// ==============================================================================
// Horizon - 抖音博主主页视频全量一键提取脚本 (在博主主页按 F12 -> Console 中粘贴回车)
// ==============================================================================
(async function() {
    console.log("🧭 Horizon Harvester 启动中... 正在扫描博主主页所有视频卡片...");
    const items = [];
    const seen = new Set();
    
    // 查找页面上的所有视频链接
    const links = document.querySelectorAll('a[href*="/video/"]');
    links.forEach(a => {
        const href = a.href;
        if (!seen.has(href)) {
            seen.add(href);
            // 获取标题
            let title = a.innerText.trim() || a.getAttribute('title') || "";
            // 如果文本包含数字或回车，清理一下
            title = title.split('\\n')[0].replace(/#|@/g, '').trim();
            if (!title) title = "未命名视频_" + href.split('/video/')[1];
            items.push({
                url: href,
                title: title,
                publish_date: new Date().toISOString().split('T')[0]
            });
        }
    });

    console.log(`✅ 成功扫描到 ${items.length} 个视频！正在下载 douyin_videos.json ...`);
    const blob = new Blob([JSON.stringify(items, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const downloadAnchor = document.createElement('a');
    downloadAnchor.href = url;
    downloadAnchor.download = 'douyin_videos.json';
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    document.body.removeChild(downloadAnchor);
    console.log("🎉 已自动下载 douyin_videos.json，直接在 Horizon 界面或脚本中上传即可开始蒸馏！");
})();
"""

def harvest_with_ytdlp(creator_url: str, output_file: Path, browser: str = "edge") -> bool:
    print(f"[*] 使用 yt-dlp 尝试从博主主页提取视频列表: {creator_url}")
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-single-json",
        "--cookies-from-browser", browser,
        creator_url
    ]
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if res.returncode == 0:
            data = json.loads(res.stdout)
            entries = data.get("entries", [])
            results = []
            for e in entries:
                v_url = e.get("url") or f"https://www.douyin.com/video/{e.get('id')}"
                v_title = e.get("title") or f"视频_{e.get('id')}"
                results.append({
                    "url": v_url,
                    "title": v_title,
                    "publish_date": e.get("upload_date")
                })
            output_file.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"[OK] 成功抓取 {len(results)} 个视频，已保存至 {output_file}")
            return True
        else:
            print(f"[!] yt-dlp 抓取遇到反爬或未获取到列表: {res.stderr[:200]}")
            return False
    except Exception as e:
        print(f"[!] 抓取异常: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="抖音博主主页全量视频抓取工具")
    parser.add_argument("--url", type=str, help="抖音博主主页 URL (例如 https://www.douyin.com/user/...)")
    parser.add_argument("--output", type=str, default="data/douyin_videos.json", help="输出 JSON 路径")
    parser.add_argument("--browser", type=str, default="edge", help="提取 Cookies 的浏览器 (edge, chrome)")
    parser.add_argument("--show_js", action="store_true", help="显示浏览器控制台一键提取代码")

    args = parser.parse_args()

    if args.show_js or not args.url:
        print("=" * 70)
        print("💡 推荐：浏览器 1 秒零风控提取法 (防抖音滑块拦截的最佳实践)")
        print("=" * 70)
        print("1. 在日常浏览器中打开该博主主页（确保您处于登录状态）；")
        print("2. 鼠标滚轮往下滚到底，让该博主的所有视频封面都加载出来；")
        print("3. 按键盘 F12（或右键 -> 检查）进入控制台 (Console)；")
        print("4. 粘贴下方代码并按回车：\n")
        print(BROWSER_HARVESTER_JS)
        print("=" * 70)
        print("浏览器将瞬间自动下载包含所有视频链接的 `douyin_videos.json`！")
        return

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    success = harvest_with_ytdlp(args.url, output_path, browser=args.browser)
    if not success:
        print("\n提示：如遇到抖音防盗链验证，请使用 --show_js 查看浏览器一键提取法。")

if __name__ == "__main__":
    main()
