"""
report_generator.py - trainingreportgenerateer
generatepackagecontainserrorframescreenshot HTMLtrainingreport. 
"""

import os
import json
import base64
from datetime import datetime
from typing import Dict, List, Optional

import cv2
import numpy as np


class ReportGenerator:
    """
    trainingreportgenerateer

    功can: 
    1. generateHTMLformat trainingreport
    2. 嵌inerrorframescreenshot
    3. displaytrainingstatisticsdata
    4. provide供improvements
    """

    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def generate_html_report(
        self,
        session_data: Dict,
        captured_frames: List[Dict],
        include_images: bool = True,
    ) -> str:
        """
        generateHTMLformat trainingreport

        Args:
            session_data: sessiondata(packagecontainssummaryetc)
            captured_frames: capture framedatalist
            include_images: YesNopackagecontains图piece(base64嵌in)

        Returns:
            generate HTMLfilepath
        """
        summary = session_data.get("summary", {})
        timestamp = session_data.get("timestamp", datetime.now().strftime("%Y%m%d_%H%M%S"))

        # generateHTMLinner容
        html = self._build_html_template(summary, captured_frames, include_images)

        # savefile
        filename = f"report_{timestamp}.html"
        filepath = os.path.join(self.output_dir, filename)

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html)

        print(f"[info] trainingreportalreadygenerate: {filepath}")
        return filepath

    def _build_html_template(
        self,
        summary: Dict,
        captured_frames: List[Dict],
        include_images: bool,
    ) -> str:
        """structbuildHTMLmockboard"""
        total_reps = summary.get("total_reps", 0)
        avg_score = summary.get("avg_score", 0)
        best_score = summary.get("best_score", 0)
        worst_score = summary.get("worst_score", 0)
        error_summary = summary.get("error_summary", {})
        reps = summary.get("reps", [])

        # scoreetc级
        score_level, score_color = self._get_score_level(avg_score)

        # errorframeHTML
        error_frames_html = self._build_error_frames_html(captured_frames, include_images)

        # perreprep_detailsHTML
        reps_html = self._build_reps_html(reps)

        # errorstatisticsHTML
        error_stats_html = self._build_error_stats_html(error_summary)

        html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Cyber Trainer - trainingreport</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        body {{
            font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        .header {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 24px;
            text-align: center;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.1);
        }}
        .header h1 {{
            font-size: 32px;
            color: #303133;
            margin-bottom: 8px;
        }}
        .header .subtitle {{
            color: #909399;
            font-size: 16px;
        }}
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 16px;
            margin-bottom: 24px;
        }}
        .stat-card {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 24px;
            text-align: center;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        }}
        .stat-value {{
            font-size: 48px;
            font-weight: bold;
            color: #409eff;
        }}
        .stat-label {{
            color: #909399;
            font-size: 14px;
            margin-top: 8px;
        }}
        .score-badge {{
            display: inline-block;
            padding: 8px 24px;
            border-radius: 24px;
            font-size: 24px;
            font-weight: bold;
            color: white;
            background: {score_color};
        }}
        .section {{
            background: rgba(255, 255, 255, 0.95);
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 24px;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.1);
        }}
        .section h2 {{
            font-size: 20px;
            color: #303133;
            margin-bottom: 16px;
            padding-bottom: 12px;
            border-bottom: 2px solid #ebeef5;
        }}
        .error-frames-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: 16px;
        }}
        .error-frame {{
            border-radius: 8px;
            overflow: hidden;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
        }}
        .error-frame img {{
            width: 100%;
            height: auto;
            display: block;
        }}
        .error-frame-info {{
            padding: 12px;
            background: #f5f7fa;
        }}
        .error-frame-info .error-type {{
            font-weight: bold;
            color: #f56c6c;
            margin-bottom: 4px;
        }}
        .error-frame-info .error-desc {{
            color: #606266;
            font-size: 14px;
        }}
        .reps-table {{
            width: 100%;
            border-collapse: collapse;
        }}
        .reps-table th,
        .reps-table td {{
            padding: 12px;
            text-align: left;
            border-bottom: 1px solid #ebeef5;
        }}
        .reps-table th {{
            background: #f5f7fa;
            font-weight: 600;
            color: #303133;
        }}
        .reps-table tr:hover {{
            background: #f5f7fa;
        }}
        .error-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 4px;
            background: #fef0f0;
            color: #f56c6c;
        }}
        .warning-tag {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 4px;
            font-size: 12px;
            margin-right: 4px;
            background: #fdf6ec;
            color: #e6a23c;
        }}
        .error-bar {{
            display: flex;
            align-items: center;
            margin-bottom: 12px;
        }}
        .error-bar-label {{
            width: 120px;
            color: #606266;
        }}
        .error-bar-track {{
            flex: 1;
            height: 24px;
            background: #ebeef5;
            border-radius: 12px;
            overflow: hidden;
        }}
        .error-bar-fill {{
            height: 100%;
            background: linear-gradient(90deg, #f56c6c, #e6a23c);
            border-radius: 12px;
            transition: width 0.3s;
        }}
        .error-bar-count {{
            width: 50px;
            text-align: right;
            color: #909399;
        }}
        .footer {{
            text-align: center;
            color: rgba(255, 255, 255, 0.8);
            padding: 24px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Cyber Trainer - trainingreport</h1>
            <p class="subtitle">squatmovementanalysisreport</p>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value">{total_reps}</div>
                <div class="stat-label">completecount</div>
            </div>
            <div class="stat-card">
                <div class="score-badge">{avg_score:.1f}</div>
                <div class="stat-label">averagescore ({score_level})</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #67c23a">{best_score:.1f}</div>
                <div class="stat-label">Besttable现</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #f56c6c">{worst_score:.1f}</div>
                <div class="stat-label">Worsttable现</div>
            </div>
        </div>

        {error_stats_html}

        {error_frames_html}

        {reps_html}

        <div class="footer">
            <p>generatetime: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>
            <p>Cyber Trainer - AIhealthbody教练system统</p>
        </div>
    </div>
</body>
</html>"""
        return html

    def _get_score_level(self, score: float) -> tuple:
        """getgetscoreetc级 color"""
        if score >= 90:
            return "优秀", "#67c23a"
        elif score >= 80:
            return "良Good", "#409eff"
        elif score >= 70:
            return " etc", "#e6a23c"
        elif score >= 60:
            return "及格", "#f56c6c"
        else:
            return "require改enter", "#f56c6c"

    def _build_error_frames_html(self, captured_frames: List[Dict], include_images: bool) -> str:
        """structbuilderrorframeHTML"""
        if not captured_frames:
            return """
            <div class="section">
                <h2>errorframescreenshot</h2>
                <p style="color: #909399; text-align: center;">thisreptraining未detectionto明显error, too棒 ! </p>
            </div>
            """

        frames_html = ""
        for frame in captured_frames:
            img_html = ""
            if include_images and frame.get("saved_path"):
                img_data = self._image_to_base64(frame["saved_path"])
                if img_data:
                    img_html = f'<img src="data:image/jpeg;base64,{img_data}" alt="error frame">'

            frames_html += f"""
            <div class="error-frame">
                {img_html}
                <div class="error-frame-info">
                    <div class="error-type">{frame.get("error_type", "未knowerror")}</div>
                    <div class="error-desc">{frame.get("error_description", "")}</div>
                    <div class="error-desc">no {frame.get("rep_number", "?")} rep | state: {frame.get("state", "?")}</div>
                </div>
            </div>
            """

        return f"""
        <div class="section">
            <h2>errorframescreenshot ({len(captured_frames)}frames)</h2>
            <div class="error-frames-grid">
                {frames_html}
            </div>
        </div>
        """

    def _build_reps_html(self, reps: List[Dict]) -> str:
        """structbuildperreprep_detailsHTML"""
        if not reps:
            return ""

        rows = ""
        for rep in reps:
            errors_html = "".join(
                f'<span class="error-tag">{e}</span>' for e in rep.get("errors", [])
            )
            warnings_html = "".join(
                f'<span class="warning-tag">{w}</span>' for w in rep.get("warnings", [])
            )

            rows += f"""
            <tr>
                <td>#{rep.get("rep_number", "?")}</td>
                <td>{rep.get("bottom_knee_angle", 0):.1f}°</td>
                <td>{rep.get("overall_score", 0):.1f}</td>
                <td>{rep.get("duration_ms", 0) / 1000:.1f}s</td>
                <td>{errors_html}{warnings_html}</td>
            </tr>
            """

        return f"""
        <div class="section">
            <h2>perreprep_details</h2>
            <table class="reps-table">
                <thead>
                    <tr>
                        <th>count</th>
                        <th>bottomknee_angle</th>
                        <th>score</th>
                        <th>usewhen</th>
                        <th>ask题</th>
                    </tr>
                </thead>
                <tbody>
                    {rows}
                </tbody>
            </table>
        </div>
        """

    def _build_error_stats_html(self, error_summary: Dict[str, int]) -> str:
        """structbuilderrorstatisticsHTML"""
        if not error_summary:
            return ""

        max_count = max(error_summary.values()) if error_summary else 1

        bars = ""
        for error_type, count in error_summary.items():
            width = (count / max_count) * 100
            bars += f"""
            <div class="error-bar">
                <div class="error-bar-label">{error_type}</div>
                <div class="error-bar-track">
                    <div class="error-bar-fill" style="width: {width}%"></div>
                </div>
                <div class="error-bar-count">{count}rep</div>
            </div>
            """

        return f"""
        <div class="section">
            <h2>errorstatistics</h2>
            {bars}
        </div>
        """

    def _image_to_base64(self, image_path: str) -> Optional[str]:
        """将图piececonvertasbase64char符string"""
        try:
            if not os.path.exists(image_path):
                return None

            with open(image_path, "rb") as f:
                image_data = f.read()

            return base64.b64encode(image_data).decode("utf-8")
        except Exception as e:
            print(f"[warning] none法read图piece {image_path}: {e}")
            return None

    def generate_mosaic_image(
        self,
        captured_frames: List[Dict],
        output_path: Optional[str] = None,
        cols: int = 3,
        thumb_width: int = 300,
    ) -> Optional[str]:
        """
        generateerrorframemosaic

        Args:
            captured_frames: capture framedatalist
            output_path: outputpath
            cols: perrowcolnum
            thumb_width: thumbnailwidth

        Returns:
            generate 图piecepath
        """
        if not captured_frames:
            return None

        # readplace 图piece
        images = []
        for frame in captured_frames:
            path = frame.get("saved_path")
            if path and os.path.exists(path):
                img = cv2.imread(path)
                if img is not None:
                    ratio = thumb_width / img.shape[1]
                    thumb = cv2.resize(img, None, fx=ratio, fy=ratio)
                    images.append(thumb)

        if not images:
            return None

        # calculate网格
        rows = (len(images) + cols - 1) // cols
        thumb_h, thumb_w = images[0].shape[:2]

        # create画布
        canvas = np.zeros((rows * thumb_h, cols * thumb_w, 3), dtype=np.uint8)

        # 填充image
        for i, img in enumerate(images):
            row = i // cols
            col = i % cols
            y = row * thumb_h
            x = col * thumb_w
            canvas[y:y+thumb_h, x:x+thumb_w] = img

        # save
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.output_dir, f"mosaic_{timestamp}.jpg")

        cv2.imwrite(output_path, canvas, [cv2.IMWRITE_JPEG_QUALITY, 90])
        print(f"[info] errorframemosaicalreadysave: {output_path}")
        return output_path
