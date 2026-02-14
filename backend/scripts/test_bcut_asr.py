# -*- coding: utf-8 -*-
# Copyright (c) 2026 relakkes@gmail.com
#
# This file is part of MediaCrawlerPro-ContentRemixAgent project.
# Repository: https://github.com/MediaCrawlerPro/MediaCrawlerPro-ContentRemixAgent/blob/main/backend/scripts/test_bcut_asr.py
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#
# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。

"""
测试 Bcut ASR 后端

使用 B站必剪云端 API 进行语音转录，并与参考字幕对比
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

# 临时修改配置使用 Bcut 后端
import config
config.settings.ASR_BACKEND = "bcut"

# 重置单例以使用新配置
from services import asr_service
asr_service.ASRService._instance = None
asr_service.BcutASRBackend._instance = None

from services.asr_service import ASRService, BcutASRBackend
from schemas import Segment


def parse_srt(srt_path: str):
    """解析 SRT 文件"""
    import re

    with open(srt_path, "r", encoding="utf-8") as f:
        content = f.read()

    segments = []
    blocks = content.strip().split("\n\n")

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) >= 3:
            index = int(lines[0])
            time_match = re.match(
                r"(\d{2}):(\d{2}):(\d{2}),(\d{3})\s*-->\s*(\d{2}):(\d{2}):(\d{2}),(\d{3})",
                lines[1]
            )
            if time_match:
                h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, time_match.groups())
                start = h1 * 3600 + m1 * 60 + s1 + ms1 / 1000
                end = h2 * 3600 + m2 * 60 + s2 + ms2 / 1000
                text = " ".join(lines[2:])
                segments.append({"index": index, "start": start, "end": end, "text": text})

    return segments


def export_srt(segments, output_path: str):
    """导出 SRT 文件"""
    with open(output_path, "w", encoding="utf-8") as f:
        for i, seg in enumerate(segments, 1):
            start_h = int(seg.start // 3600)
            start_m = int((seg.start % 3600) // 60)
            start_s = int(seg.start % 60)
            start_ms = int((seg.start % 1) * 1000)

            end_h = int(seg.end // 3600)
            end_m = int((seg.end % 3600) // 60)
            end_s = int(seg.end % 60)
            end_ms = int((seg.end % 1) * 1000)

            f.write(f"{i}\n")
            f.write(f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d} --> ")
            f.write(f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}\n")
            f.write(f"{seg.text}\n\n")


def format_time(seconds: float) -> str:
    """格式化时间"""
    m = int(seconds // 60)
    s = seconds % 60
    return f"{m:02d}:{s:05.2f}"


def main():
    # 路径配置
    video_path = Path(__file__).parent.parent / "assets/bilibili/BV1eNrkB5ECx/video.mp4"
    ref_srt_path = Path(__file__).parent.parent / "assets/bilibili/BV1eNrkB5ECx/最终完成版本.srt"
    output_srt_path = Path(__file__).parent.parent / "assets/bilibili/BV1eNrkB5ECx/bcut_output.srt"

    print("=" * 80)
    print("Bcut ASR 测试")
    print("=" * 80)
    print(f"视频文件: {video_path}")
    print(f"参考字幕: {ref_srt_path}")

    # 检查文件
    if not video_path.exists():
        print(f"错误: 视频文件不存在: {video_path}")
        return

    if not ref_srt_path.exists():
        print(f"错误: 参考字幕不存在: {ref_srt_path}")
        return

    # 解析参考字幕
    print("\n正在解析参考字幕...")
    ref_segments = parse_srt(str(ref_srt_path))
    print(f"参考字幕: {len(ref_segments)} 段")

    # 初始化 ASR 服务
    print("\n正在初始化 Bcut ASR 服务...")
    asr_service = ASRService()
    print(f"当前后端: {asr_service.backend_name}")

    if not asr_service.is_available():
        print("错误: Bcut ASR 不可用")
        return

    # 运行 ASR
    print("\n正在调用 Bcut API 进行转录...")
    print("(需要上传音频到 B站服务器，请耐心等待)")

    try:
        result = asr_service.transcribe(str(video_path))
    except Exception as e:
        print(f"ASR 错误: {e}")
        import traceback
        traceback.print_exc()
        return

    print(f"\nBcut ASR 结果: {len(result.text)} 字符, {len(result.segments)} 段")

    # 导出 SRT
    export_srt(result.segments, str(output_srt_path))
    print(f"\nBcut ASR 结果已导出: {output_srt_path}")

    # 统计指标
    print("\n" + "=" * 80)
    print("统计指标")
    print("=" * 80)
    ref_text = "".join(s["text"] for s in ref_segments)
    print(f"Bcut 字符数: {len(result.text)}")
    print(f"REF 字符数: {len(ref_text)}")
    print(f"Bcut 分段数: {len(result.segments)}")
    print(f"REF 分段数: {len(ref_segments)}")

    # 全文对比
    print("\n" + "=" * 80)
    print("全文对比")
    print("=" * 80)
    print("\n[Bcut 全文]")
    print(result.text[:500] + "..." if len(result.text) > 500 else result.text)
    print("\n[REF 全文]")
    print(ref_text[:500] + "..." if len(ref_text) > 500 else ref_text)

    # 分段对比 (前20段)
    print("\n" + "=" * 80)
    print("分段对比 (前20段)")
    print("=" * 80)

    for i in range(min(20, len(result.segments), len(ref_segments))):
        bcut_seg = result.segments[i]
        ref_seg = ref_segments[i]

        print(f"\n[{i+1}] 时间: Bcut {format_time(bcut_seg.start)}-{format_time(bcut_seg.end)} | REF {format_time(ref_seg['start'])}-{format_time(ref_seg['end'])}")
        print(f"  Bcut: {bcut_seg.text}")
        print(f"  REF:  {ref_seg['text']}")

        if bcut_seg.text != ref_seg['text']:
            print(f"  >>> 差异")

    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    main()
